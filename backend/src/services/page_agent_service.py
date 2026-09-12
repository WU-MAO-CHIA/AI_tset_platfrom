"""Autonomous page-exploration agent (ReAct over plain text).

The loop works with every LLM provider (Anthropic / OpenAI / Ollama) because
tool calls are plain JSON in a ```tool fenced block — no native function
calling required.

Credential policy: login values are resolved server-side from the case's
test-data variables and NEVER appear in prompts, observations or logs;
every occurrence is masked as ***.
"""

import asyncio
import json
import re
from typing import Any, Awaitable, Callable, Optional

from src.core.llm_provider import LLMProvider
from src.services.page_explorer_service import PageExplorerService

MASK = "***"
TOOL_RE = re.compile(r"```tool\s*(\{.*?\})\s*```", re.DOTALL)

EXPLORER_SYSTEM_PROMPT = """\
你是一位網頁探索助手，負責在真實網頁上找到使用者指定的目標元素，
並回報每個元素可用的定位器（建議 locator、相對 XPath、CSS）。

## 可用工具（每次回應只能呼叫一個工具，用 ```tool JSON 區塊表示）
- {"action": "snapshot"}：列出目前頁面可見的可互動元素（ref 如 e0、e1…）
- {"action": "click", "ref": "e3"}：點擊元素
- {"action": "fill", "ref": "e1", "variable": "${USERNAME}"}：填入登入資訊。
  只能用 variable（test-data 變數名），絕對不要輸出真實帳號密碼。
- {"action": "get_locators", "ref": "e3"}：取得該元素的定位器三件套
- {"action": "finish", "findings": [{"goal": "登入按鈕", "ref": "e3", "status": "found|not_found", "note": "..."}]}：結束探索

## 規則
1. 先 snapshot，再針對每個 goal 用 get_locators 取得定位器；需要換頁/登入才 click/fill。
2. 找不到就標 not_found 並說明卡點（如遇到驗證碼），不要硬闖、不要猜測 XPath。
3. 憑證只能用 variable 引用；若缺少所需變數，直接 finish 並在 note 說明缺哪個變數。
4. 回應格式：先用 1-2 句中文說明打算做什麼，再附 ```tool 區塊。
"""


class PageAgentService:
    def __init__(
        self,
        provider: LLMProvider,
        explorer_factory: Optional[Callable[[], PageExplorerService]] = None,
        max_steps: int = 12,
        step_timeout_sec: float = 60.0,
    ) -> None:
        self.provider = provider
        self.explorer_factory = explorer_factory or PageExplorerService
        self.max_steps = max_steps
        self.step_timeout_sec = step_timeout_sec

    @staticmethod
    def mask_secrets(text: str, secrets: list[str]) -> str:
        for s in secrets:
            if s and len(s) >= 2 and s in text:
                text = text.replace(s, MASK)
        return text

    @staticmethod
    def parse_tool_call(raw: str) -> Optional[dict]:
        m = TOOL_RE.search(raw or "")
        if not m:
            return None
        try:
            data = json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            return None
        return data if isinstance(data, dict) and data.get("action") else None

    def _narrative(self, raw: str) -> str:
        """LLM 回應中 ```tool 區塊以外的說明文字。"""
        return TOOL_RE.sub("", raw or "").strip()[:500]

    async def explore(
        self,
        url: str,
        goals: list[str],
        credentials: Optional[dict[str, str]] = None,
        on_step: Optional[Callable[[dict], Awaitable[None]]] = None,
    ) -> dict:
        """Run the exploration loop. Returns {status, catalog, steps_used, note}."""
        credentials = credentials or {}
        secrets = [v for v in credentials.values() if v]
        explorer: PageExplorerService = self.explorer_factory()

        async def emit(step: dict) -> None:
            if on_step:
                await on_step(step)

        catalog: list[dict] = []
        try:
            await explorer.start()
            try:
                nav = await explorer.goto(url)
            except Exception as exc:
                return {"status": "error", "catalog": [], "steps_used": 0,
                        "note": f"無法開啟網址：{exc}"}

            history: list[dict] = [{
                "role": "user",
                "content": (
                    f"目標網址：{nav.get('url', url)}（標題：{nav.get('title', '')}）\n"
                    f"請找到以下目標元素：\n"
                    + "\n".join(f"- {g}" for g in goals)
                    + ("\n可用登入變數：" + ", ".join(sorted(credentials)) if credentials else "\n無登入變數（若需登入請直接 finish 說明）")
                ),
            }]

            steps_used = 0
            for _ in range(self.max_steps):
                steps_used += 1
                try:
                    raw = await asyncio.wait_for(
                        self.provider.complete_with_messages(history, system=EXPLORER_SYSTEM_PROMPT),
                        timeout=self.step_timeout_sec,
                    )
                except asyncio.TimeoutError:
                    history.append({"role": "user", "content": "上一步 AI 回應逾時，請重發上一個工具呼叫。"})
                    await emit({"step": steps_used, "action": "llm_timeout"})
                    continue
                except Exception as exc:
                    return {"status": "error", "catalog": self._catalog_fallback(catalog),
                            "steps_used": steps_used, "note": f"AI 呼叫失敗：{exc}"}

                call = self.parse_tool_call(raw)
                narrative = self._narrative(raw)
                if call is None:
                    obs = "無法解析工具呼叫。請只用 ```tool JSON 區塊回應，例如：```tool\n{\"action\": \"snapshot\"}\n```"
                    history += [{"role": "assistant", "content": raw},
                                {"role": "user", "content": obs}]
                    await emit({"step": steps_used, "action": "parse_error", "narrative": narrative})
                    continue

                action = call.get("action")
                await emit({"step": steps_used, "action": action, "narrative": narrative})

                if action == "finish":
                    return await self._finish(explorer, call, catalog, steps_used)

                obs = await self._execute_tool(explorer, call, credentials)
                obs = self.mask_secrets(str(obs)[:4000], secrets)
                history += [{"role": "assistant", "content": raw},
                            {"role": "user", "content": f"工具結果：\n{obs}\n請繼續（必要時 finish）。"}]

            return {"status": "partial", "catalog": self._catalog_fallback(catalog),
                    "steps_used": steps_used, "note": f"已達步數上限（{self.max_steps}）"}
        finally:
            await explorer.close()

    async def _execute_tool(
        self,
        explorer: PageExplorerService,
        call: dict,
        credentials: dict[str, str],
    ) -> Any:
        action = call.get("action")
        try:
            if action == "snapshot":
                snap = await explorer.snapshot()
                lines = [f"url={snap.get('url')} title={snap.get('title')} "
                         f"共 {snap.get('total')} 個元素" + ("（已截斷）" if snap.get("truncated") else "")]
                for el in snap["elements"]:
                    lines.append(f"{el['ref']}: [{el.get('role') or el.get('tag')}] {el.get('name') or '(無名稱)'} <{el.get('tag')}>")
                return "\n".join(lines)
            if action == "click":
                return await explorer.click(call.get("ref", ""))
            if action == "fill":
                raw_var = (call.get("variable", "") or "").strip()
                # Keys in `credentials` are upper-cased (see _resolve_credential_vars),
                # so normalize here too — ${username} must match USERNAME.
                var = raw_var.removeprefix("${").removesuffix("}").upper()
                if not var or var not in credentials:
                    available = ", ".join(sorted(credentials)) or "（無）"
                    return f"錯誤：缺少登入變數 {raw_var or '(空)'}，可用變數：{available}。請 finish 並在 note 說明。"
                return await explorer.fill(call.get("ref", ""), credentials[var])
            if action == "get_locators":
                return await explorer.get_locators(call.get("ref", ""))
            return f"錯誤：未知工具 {action}。可用：snapshot / click / fill / get_locators / finish。"
        except Exception as exc:
            return f"工具執行失敗：{exc}"

    async def _finish(
        self,
        explorer: PageExplorerService,
        call: dict,
        catalog: list[dict],
        steps_used: int,
    ) -> dict:
        for f in call.get("findings", []) or []:
            entry: dict = {
                "goal": f.get("goal", ""),
                "status": f.get("status", "not_found"),
                "note": f.get("note", ""),
                "ref": f.get("ref", ""),
                "role": "", "name": "",
                "recommended": "", "xpath": "", "css": "",
                "xpath_unique": False,
            }
            if f.get("status") == "found" and f.get("ref"):
                try:
                    loc = await explorer.get_locators(f["ref"])
                    entry.update({k: loc.get(k, entry[k]) for k in
                                  ("role", "name", "recommended", "xpath", "css", "xpath_unique")})
                except Exception as exc:
                    entry["status"] = "not_found"
                    entry["note"] = f"取得定位器失敗：{exc}"
            catalog.append(entry)
        found = sum(1 for c in catalog if c["status"] == "found")
        return {"status": "done" if found else "empty", "catalog": catalog,
                "steps_used": steps_used,
                "note": f"找到 {found}/{len(catalog)} 個目標"}

    @staticmethod
    def _catalog_fallback(catalog: list[dict]) -> list[dict]:
        return catalog
