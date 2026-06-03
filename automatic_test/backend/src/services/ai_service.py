import asyncio
from typing import Optional

from src.core.llm_provider import LLMProvider

_CHAT_SYSTEM_PROMPT = """\
你是一位專業的軟體測試工程師，負責協助撰寫測試案例步驟與 Robot Framework 腳本。

使用者會描述需要測試的功能，你需要：
1. 提供清楚的測試步驟建議（以自然語言對話方式）
2. 同時生成對應的 Robot Framework (.robot) 腳本（使用 Browser library/Playwright）

你的回應必須嚴格遵循以下格式（含分隔線）：
---MESSAGE---
（你的對話回應，解釋測試思路、步驟建議，或向使用者提問）
---RF_CODE---
（Robot Framework .robot 腳本內容，以 *** Settings *** 開頭；若步驟不足以生成腳本，填入 # 尚無足夠資訊）
---END---"""

_COMPLETE_STEPS_PROMPT = """\
你是一位專業的軟體測試工程師，請根據以下資訊補齊測試步驟：

功能描述：{description}

已有步驟：
{partial_steps}

請補齊完整的測試步驟，格式為「1. xxx\n2. xxx\n...」，每步驟清晰、可執行，步驟應包含預期結果驗證。
只回傳步驟列表，不加其他說明。"""

_PREVIEW_ROBOT_PROMPT = """\
將以下測試步驟轉換為 Robot Framework 格式的 .robot 腳本，使用 Browser library（Playwright）。

測試步驟：
{main_steps}

若步驟過於模糊無法轉換，請只回傳：UNABLE_TO_GENERATE: <原因>

否則只回傳 .robot 腳本內容，範例格式：
*** Settings ***
Library    Browser

*** Test Cases ***
測試案例名稱
    [Documentation]    自動生成
    ...
"""

_GENERATE_ROBOT_PROMPT = """\
將以下測試步驟轉換為 Robot Framework 格式的 .robot 腳本，使用 Browser library（Playwright）。

測試案例編號：{case_number}
測試案例名稱：{case_name}
測試步驟：
{main_steps}

若步驟過於模糊無法轉換，請只回傳：UNABLE_TO_GENERATE: <原因>

否則只回傳 .robot 腳本內容：
*** Settings ***
Library    Browser

*** Test Cases ***
{case_name}
    [Documentation]    {case_number}
    ...
"""


class AIService:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._code_cache: dict[str, str | None] = {}

    async def complete_steps(
        self,
        partial_steps: str,
        description: str = "",
        media_attachments: Optional[list] = None,
    ) -> str:
        prompt = _COMPLETE_STEPS_PROMPT.format(
            description=description or "(未提供)",
            partial_steps=partial_steps,
        )

        if media_attachments:
            return await self.provider.complete_with_vision(prompt, media_attachments)
        return await self.provider.complete(prompt)

    async def generate_robot_code(
        self,
        case_number: str,
        case_name: str,
        main_steps: str,
        case_version: int,
        llm_model: Optional[str] = None,
        timeout_sec: float = 35.0,
    ) -> Optional[str]:
        """Generate Robot Framework code from natural language steps.
        Returns None when:
        - LLM marks steps as UNABLE_TO_GENERATE
        - Timeout exceeded
        """
        cache_key = f"{case_number}:v{case_version}"
        cached = await self._get_cached_code(cache_key)
        if cached is not None:
            if cached.generation_status == "success":
                return cached.code_content
            return None

        prompt = _GENERATE_ROBOT_PROMPT.format(
            case_number=case_number,
            case_name=case_name,
            main_steps=main_steps,
        )
        try:
            code = await asyncio.wait_for(
                self.provider.complete(prompt),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            await self._cache_code(cache_key, None, "failed", "Timeout exceeded")
            return None
        except Exception as exc:
            await self._cache_code(cache_key, None, "failed", str(exc))
            return None

        if code and code.strip().startswith("UNABLE_TO_GENERATE"):
            await self._cache_code(cache_key, None, "unable_to_generate", code.strip())
            return None

        await self._cache_code(cache_key, code, "success", None)
        return code

    async def preview_robot_code(
        self,
        main_steps: str,
        llm_model: Optional[str] = None,
        timeout_sec: float = 35.0,
    ) -> Optional[str]:
        """Generate RF preview from steps without case metadata or caching."""
        prompt = _PREVIEW_ROBOT_PROMPT.format(main_steps=main_steps)
        try:
            code = await asyncio.wait_for(
                self.provider.complete(prompt),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            return None
        except Exception:
            return None

        if code and code.strip().startswith("UNABLE_TO_GENERATE"):
            return None
        return code

    async def chat_and_generate_rf(
        self,
        messages: list[dict],
        user_message: str,
        llm_model: str,
        timeout_sec: float = 35.0,
    ) -> dict:
        """Multi-turn chat that returns assistant reply and RF code.

        messages: existing history [{role, content}]
        Returns { assistant_message: str, rf_code: str }
        """
        conversation = [*messages, {"role": "user", "content": user_message}]
        try:
            raw = await asyncio.wait_for(
                self.provider.complete_with_messages(conversation, system=_CHAT_SYSTEM_PROMPT),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            return {"assistant_message": "抱歉，回應逾時，請稍後再試。", "rf_code": ""}
        except Exception as exc:
            return {"assistant_message": f"抱歉，AI 服務發生錯誤：{exc}", "rf_code": ""}

        assistant_message, rf_code = self._parse_chat_response(raw)
        return {"assistant_message": assistant_message, "rf_code": rf_code}

    def _parse_chat_response(self, raw: str) -> tuple[str, str]:
        """Parse the structured chat response into (message, rf_code).

        Handles cases where LLM omits ---MESSAGE--- or ---END--- markers by
        anchoring on ---RF_CODE--- which is the most reliably present delimiter.
        """
        rf_marker = "---RF_CODE---"
        end_marker = "---END---"
        msg_marker = "---MESSAGE---"

        if rf_marker in raw:
            rf_idx = raw.index(rf_marker)
            message_part = raw[:rf_idx]
            if msg_marker in message_part:
                message_part = message_part[message_part.index(msg_marker) + len(msg_marker):]
            assistant_message = message_part.strip()

            rf_content_start = rf_idx + len(rf_marker)
            rf_content = raw[rf_content_start:raw.index(end_marker)].strip() if end_marker in raw else raw[rf_content_start:].strip()
            return assistant_message, rf_content

        if msg_marker in raw:
            return raw[raw.index(msg_marker) + len(msg_marker):].strip(), ""
        return raw.strip(), ""

    async def _get_cached_code(self, cache_key: str):
        if cache_key in self._code_cache:
            return self._code_cache[cache_key]
        return None

    async def _cache_code(self, cache_key: str, code: Optional[str], status: str, error: Optional[str]) -> None:
        from collections import namedtuple
        CacheEntry = namedtuple("CacheEntry", ["code_content", "generation_status", "error_message"])
        self._code_cache[cache_key] = CacheEntry(code_content=code, generation_status=status, error_message=error)
