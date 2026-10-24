import asyncio
import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.llm_provider import LLMProvider

# prompt 列出的 keyword 皆存在於 Browser library（tests/unit/test_ai_service_rf_rules.py 以 libdoc 驗證）
_BROWSER_KEYWORDS = (
    "New Browser", "New Context", "New Page", "Go To", "Close Browser", "Set Browser Timeout",
    "Click", "Fill Text", "Fill Secret", "Type Text", "Clear Text", "Press Keys", "Keyboard Key",
    "Check Checkbox", "Uncheck Checkbox", "Select Options By", "Hover", "Upload File By Selector",
    "Get Text", "Get Url", "Get Title", "Get Element Count", "Get Attribute", "Get Property",
    "Get Checkbox State", "Wait For Elements State", "Wait For Load State", "Take Screenshot",
)
# SeleniumLibrary 專有、Browser library 沒有的 keyword（LLM 最常誤用）
_SELENIUM_ONLY_KEYWORDS = (
    "Input Text", "Input Password", "Click Element", "Click Button", "Page Should Contain",
    "Element Should Be Visible", "Wait Until Element Is Visible", "Wait Until Page Contains",
)

# 所有 prompt 一律以單層大括號撰寫（即 LLM 實際看到的 RF 語法），
# 填入 placeholder 時用 _render_prompt，不用 str.format。
_RF_RULES = """\
RF 腳本必須遵守以下規則（Robot Framework 7 + Browser library）：

【結構】
- 只使用 Browser library（Playwright），Settings 區塊宣告：Library    Browser。切勿使用或混用 SeleniumLibrary。
- 每個 Test Case 都要能單獨執行：Test Setup 呼叫自訂 keyword，依序執行 New Browser（chromium, headless=True）、New Context、New Page 並開啟 ${BASE_URL}；Test Teardown 呼叫 Close Browser。不要使用 Suite Setup / Suite Teardown。
- 每個 *** Test Cases *** 條目必須含 [Documentation] 與 [Tags]。
- keyword 與參數之間至少以 4 個空白分隔；變數一律寫成 ${NAME}（單層大括號）。

【定位器：只能使用有根據的 locator】
依下列來源順序選擇：
1. 「KNOWN PAGE ELEMENTS」區塊或既有 RF 程式碼中的 locator：有就必須沿用，不得改寫。
2. 使用者在步驟或對話中明確提供的 id、name、CSS 或 XPath。
3. 由步驟中出現的可見文字推導（欄位的標籤或 placeholder 文字都可當作 name）：
   - 按鈕／連結：role=button[name="登入"]、role=link[name="忘記密碼"]
   - 輸入欄（密碼欄也適用）：role=textbox[name="帳號"]
   - 下拉選單：role=combobox[name="..."]；勾選框：role=checkbox[name="..."]
   - 其他可見文字：text="..."
- 禁止編造來源中沒有出現的 id、name、class、data-testid，包括框架自動產生的 id（例如 ASP.NET 的 ContentPlaceHolder1_xxx、ctl00_xxx）。
- 禁止使用絕對 XPath（如 //div[3]/span[1]）。
- 元素位於 iframe 內時，以「iframe 的 locator >>> 元素的 locator」串接。
- 依第 3 點推導、尚未證實存在的 locator，在該步驟上一行加註：# TODO: locator 未驗證

【等待與斷言】
- Click、Fill Text 等互動 keyword 會自動等待元素可操作，不必先加 Wait For Elements State；禁止用 Sleep 等待畫面。
- 步驟中每個「預期結果／驗證／確認」都必須寫成斷言。Browser 的 Get 系列 keyword 可直接斷言，並會自動重試到逾時：
    Get Text    <locator>    ==    <完整文字>        （部分符合用 *=）
    Get Url    *=    <網址片段>                     （不應包含用 not contains）
    Get Title    ==    <頁面標題>
    Get Element Count    <locator>    ==    0
    Wait For Elements State    <locator>    visible    （消失用 hidden 或 detached）
- 斷言使用的文字與網址只能取自步驟描述，不可編造成功頁的元素或文案。若預期結果很模糊（例如只寫「登入成功」），改為斷言可觀察的變化（例如 Get Url    not contains    login，或登入按鈕消失），並加註：# TODO: 請確認成功判斷依據

【變數與機密】
- 網址、帳號、密碼等測試資料放在 *** Variables ***（例如 ${BASE_URL}、${USERNAME}、${PASSWORD}），步驟中以變數引用，不要寫死在步驟裡。
- ${BASE_URL} 使用步驟中提供的網址；沒有提供網址時寫成「${BASE_URL}    請填入受測網址」，不要自行假設網址，也不要使用 localhost。
- 密碼等機密欄位一律寫成：Fill Secret    <locator>    $PASSWORD
  第二個參數是「$ + 變數名稱」且不加大括號，寫成 ${PASSWORD} 會執行失敗。Fill Secret 不會把機密寫進執行 log。

【可用的 keyword】
只使用以下 Browser keyword，以及 BuiltIn keyword（如 Log、Should Be Equal、Run Keyword And Return Status）與 IF / FOR 語法：
""" + "、".join(_BROWSER_KEYWORDS) + """
SeleniumLibrary 的 keyword 在 Browser library 中不存在，禁止使用，例如：""" + "、".join(_SELENIUM_ONLY_KEYWORDS) + """。
也不要使用 Browser 的 Open Browser：它預設開啟有畫面的瀏覽器，僅供手動除錯。

CAPTCHA 處理規則（當測試頁面可能出現圖形驗證碼時必須遵守）：
- Settings 區塊額外匯入 CaptchaSolverLibrary（與 Browser library 並列）：
    Library    ${CURDIR}/../libs/CaptchaSolverLibrary.py
- 在 *** Keywords *** 區塊定義「處理圖形驗證碼（如存在）」keyword，範本如下
  （請將 <CAPTCHA圖片selector> / <CAPTCHA輸入欄selector> 替換為依上述定位器規則取得的 selector）：

處理圖形驗證碼（如存在）
    [Documentation]    若頁面存在圖形驗證碼，截圖後以 Claude Vision 辨識並填入
    ${captcha_visible}=    Run Keyword And Return Status
    ...    Wait For Elements State    <CAPTCHA圖片selector>    visible    timeout=3s
    IF    ${captcha_visible}
        ${captcha_path}=    Take Screenshot
        ...    filename=${OUTPUT DIR}/captcha_${TEST NAME}.png
        ...    selector=<CAPTCHA圖片selector>
        ...    fullPage=False
        ${captcha_text}=    Solve Captcha From File    ${captcha_path}
        Log    CAPTCHA 辨識結果：${captcha_text}
        Fill Text    <CAPTCHA輸入欄selector>    ${captcha_text}
    END

- 在填完帳號密碼後、點擊送出按鈕前，呼叫：處理圖形驗證碼（如存在）
- 此 keyword 採「若存在才處理」設計：若頁面無 CAPTCHA 元素則自動略過，不影響正常流程
"""

_CHAT_SYSTEM_PROMPT = """\
你是一位專業的軟體測試工程師，負責協助撰寫測試案例步驟與 Robot Framework 腳本。

使用者會描述需要測試的功能，你需要：
1. 提供清楚的測試步驟建議（以自然語言對話方式）
2. 同時生成對應的 Robot Framework (.robot) 腳本

""" + _RF_RULES + """
你的回應必須嚴格遵循以下格式（含分隔線）：
---MESSAGE---
（你的對話回應：解釋測試思路與步驟建議，或向使用者提問。若腳本中有標記 TODO 的 locator 或斷言，逐一列出，並建議先執行「頁面探索」取得真實定位器）
---RF_CODE---
（完整的 .robot 腳本，以 *** Settings *** 開頭，不要加 Markdown 程式碼框（```）；若資訊不足以生成腳本，只填入：# 尚無足夠資訊）
---END---"""

_COMPLETE_STEPS_PROMPT = """\
你是一位專業的軟體測試工程師，請根據以下資訊補齊測試步驟：

功能描述：{description}

已有步驟：
{partial_steps}

請補齊完整的測試步驟，格式為「1. xxx\n2. xxx\n...」，每步驟清晰、可執行，步驟應包含預期結果驗證。
只回傳步驟列表，不加其他說明。"""

_SCRIPT_OUTPUT_RULES = """\
輸出規則：
- 若步驟過於模糊、無法轉換成可執行的操作，只回傳一行：UNABLE_TO_GENERATE: <原因>
- 否則只回傳 .robot 腳本本身：從 *** Settings *** 開始，不要加 Markdown 程式碼框（```），也不要加任何說明文字。
"""

_SCRIPT_SKELETON = """\
*** Settings ***
Library    Browser
Test Setup       Open Test Browser
Test Teardown    Close Browser

*** Variables ***
${BASE_URL}    <步驟中提供的受測網址>

*** Keywords ***
Open Test Browser
    New Browser    chromium    headless=True
    New Context
    New Page    ${BASE_URL}

*** Test Cases ***
<TEST_NAME>
    [Documentation]    <DOCUMENTATION>
    [Tags]    <TAGS>
    # 依測試步驟填入互動與斷言，例如：
    # Fill Text    role=textbox[name="帳號"]    ${USERNAME}
    # Fill Secret    role=textbox[name="密碼"]    $PASSWORD
    # Click    role=button[name="登入"]
    # Get Text    role=heading    ==    歡迎回來
"""

_PREVIEW_ROBOT_PROMPT = (
    "將以下測試步驟轉換為 Robot Framework 格式的 .robot 腳本。\n\n"
    + _RF_RULES
    + "\n測試步驟：\n{main_steps}\n\n"
    + _SCRIPT_OUTPUT_RULES
    + "\n骨架範例（請依實際步驟填入）：\n"
    + _SCRIPT_SKELETON.replace("<TEST_NAME>", "測試案例名稱")
    .replace("<DOCUMENTATION>", "<一句話說明測試目的>")
    .replace("<TAGS>", "auto-generated")
)

_GENERATE_ROBOT_PROMPT = (
    "將以下測試步驟轉換為 Robot Framework 格式的 .robot 腳本。\n\n"
    + _RF_RULES
    + "\n測試案例編號：{case_number}\n測試案例名稱：{case_name}\n測試步驟：\n{main_steps}\n\n"
    + _SCRIPT_OUTPUT_RULES
    + "\n骨架範例（請依實際步驟填入）：\n"
    + _SCRIPT_SKELETON.replace("<TEST_NAME>", "{case_name}")
    .replace("<DOCUMENTATION>", "{case_number} - <一句話說明測試目的>")
    .replace("<TAGS>", "auto-generated    case-{case_number}")
)

_PLACEHOLDER_RE = re.compile(r"\{(case_number|case_name|main_steps)\}")
_CODE_FENCE_RE = re.compile(r"```[\w-]*[ \t]*\r?\n(.*?)(?:\r?\n)?[ \t]*```", re.DOTALL)


def _render_prompt(template: str, **values: str) -> str:
    """一次替換 {case_number} 等 placeholder；RF 的 ${VAR} 原樣保留，填入的值也不會再被解析。"""
    return _PLACEHOLDER_RE.sub(lambda m: values.get(m.group(1), m.group(0)), template)


def _strip_code_fences(code: Optional[str]) -> Optional[str]:
    """LLM 仍可能用 ``` 包住腳本；結尾那行 ``` 會被 RF 當成空的 test case 而失敗，故取出框內內容。"""
    if not code or "```" not in code:
        return code
    m = _CODE_FENCE_RE.search(code)
    return m.group(1) if m else code


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
        session: Optional[AsyncSession] = None,
    ) -> Optional[str]:
        """Generate Robot Framework code from natural language steps.
        Returns None when:
        - LLM marks steps as UNABLE_TO_GENERATE
        - Timeout exceeded
        
        If session is provided, checks DB (RobotScript table) first and persists on success.
        """
        cache_key = f"{case_number}:v{case_version}"
        cached = await self._get_cached_code(cache_key)
        if cached is not None:
            if cached.generation_status == "success":
                return cached.code_content
            return None

        if session is not None:
            from src.repositories.robot_script_repo import RobotScriptRepository
            from src.repositories.test_case_repo import TestCaseRepository
            case_repo = TestCaseRepository(session)
            case = await case_repo.get_by_case_number(case_number)
            if case:
                robot_repo = RobotScriptRepository(session)
                record = await robot_repo.get_by_case_id(case.id)
                if record and record.rf_code:
                    await self._cache_code(cache_key, record.rf_code, "success", None)
                    return record.rf_code

        prompt = _render_prompt(
            _GENERATE_ROBOT_PROMPT,
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

        code = _strip_code_fences(code)
        if code and code.strip().startswith("UNABLE_TO_GENERATE"):
            await self._cache_code(cache_key, None, "unable_to_generate", code.strip())
            return None

        await self._cache_code(cache_key, code, "success", None)

        if session is not None:
            from src.repositories.robot_script_repo import RobotScriptRepository
            from src.repositories.test_case_repo import TestCaseRepository
            case_repo = TestCaseRepository(session)
            case = await case_repo.get_by_case_number(case_number)
            if case:
                robot_repo = RobotScriptRepository(session)
                await robot_repo.upsert(test_case_id=case.id, rf_code=code)

        return code

    async def preview_robot_code(
        self,
        main_steps: str,
        llm_model: Optional[str] = None,
        timeout_sec: float = 35.0,
    ) -> Optional[str]:
        """Generate RF preview from steps without case metadata or caching."""
        prompt = _render_prompt(_PREVIEW_ROBOT_PROMPT, main_steps=main_steps)
        try:
            code = await asyncio.wait_for(
                self.provider.complete(prompt),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            return None
        except Exception:
            return None

        code = _strip_code_fences(code)
        if code and code.strip().startswith("UNABLE_TO_GENERATE"):
            return None
        return code

    def _build_catalog_block(self, catalog: list[dict]) -> str:
        """Render an element-catalog context block (capped for prompt size)."""
        lines = []
        for entry in (catalog or [])[:30]:
            if not isinstance(entry, dict):
                continue
            goal = str(entry.get("goal", "")).strip()
            rec = str(entry.get("recommended", "")).strip()
            xpath = str(entry.get("xpath", "")).strip()
            css = str(entry.get("css", "")).strip()
            if entry.get("status", "found") != "found" or not (rec or xpath):
                lines.append(f"- {goal or '(未知目標)'}：未找到（{entry.get('note', '')}），請依測試步驟描述推導，切勿編造 XPath")
                continue
            unique_mark = "" if entry.get("xpath_unique") else "｜注意：此 XPath 非唯一，選用前請確認"
            lines.append(f"- {goal}｜建議: {rec}｜XPath: {xpath}｜CSS: {css}{unique_mark}")
        if not lines:
            return ""
        return ("\n\n---KNOWN PAGE ELEMENTS---\n以下為頁面探索取得的真實定位器；已找到的目標必須沿用，不得改寫或另行編造：\n"
                "「建議」欄已符合 role=/text= 優先序；XPath 皆為相對路徑，`xpath_unique` 為 false 者表示該 XPath 非唯一、"
                "僅供參考，選用前請要求使用者確認或改用建議 locator：\n"
                + "\n".join(lines) + "\n---END PAGE ELEMENTS---")

    def _build_rf_context_block(self, rf_code: str, mode: str) -> str:
        """Build RF code context block for system prompt based on mode."""
        if mode == "full":
            return f"\n\n---UPLOADED RF CODE---\n{rf_code}\n---END RF CODE---"
        elif mode == "summary":
            # Generate a concise summary of the RF code
            lines = rf_code.strip().split("\n")
            # Extract key sections: Settings, Test Cases names, Keywords
            summary_lines = []
            in_test_case = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("*** Settings ***") or stripped.startswith("*** Variables ***") or stripped.startswith("*** Keywords ***"):
                    summary_lines.append(stripped)
                elif stripped.startswith("*** Test Cases ***"):
                    summary_lines.append(stripped)
                    in_test_case = True
                elif in_test_case and stripped and not stripped.startswith("#"):
                    # Capture test case names (lines not indented with spaces/tabs)
                    if not line.startswith(" ") and not line.startswith("\t") and stripped:
                        summary_lines.append(f"  {stripped}")
            summary = "\n".join(summary_lines[:30])  # Limit summary length
            if len(summary) > 1000:
                summary = summary[:1000] + "\n... (truncated)"
            return f"\n\n---UPLOADED RF CODE (SUMMARY)---\n{summary}\n---END RF CODE---"
        return ""

    async def chat_and_generate_rf(
        self,
        messages: list[dict],
        user_message: str,
        llm_model: str,
        rf_code: Optional[str] = None,
        rf_context_mode: str = "full",
        element_catalog: Optional[list[dict]] = None,
        timeout_sec: float = 35.0,
    ) -> dict:
        """Multi-turn chat that returns assistant reply and RF code.

        messages: existing history [{role, content}]
        user_message: current user message
        llm_model: model identifier
        rf_code: optional RF code to inject as context
        rf_context_mode: "full" | "summary" | "none"
        element_catalog: optional page-exploration results
            [{goal, recommended, xpath, css, ...}] — injected so generated
            selectors match the real page instead of guesses.
        Returns { assistant_message: str, rf_code: str }
        """
        # Build system prompt with optional RF code context
        system_prompt = _CHAT_SYSTEM_PROMPT
        if rf_code and rf_code.strip() and rf_context_mode != "none":
            system_prompt += self._build_rf_context_block(rf_code, rf_context_mode)
        if element_catalog:
            system_prompt += self._build_catalog_block(element_catalog)

        conversation = [*messages, {"role": "user", "content": user_message}]
        try:
            raw = await asyncio.wait_for(
                # 固定的規則可快取；其後的 RF 程式碼與頁面元素每次可能不同
                self.provider.complete_with_messages(
                    conversation, system=system_prompt, cache_prefix=_CHAT_SYSTEM_PROMPT,
                ),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            return {"assistant_message": "抱歉，回應逾時，請稍後再試。", "rf_code": ""}
        except Exception as exc:
            return {"assistant_message": f"抱歉，AI 服務發生錯誤：{exc}", "rf_code": ""}

        assistant_message, rf_code_result = self._parse_chat_response(raw)
        return {"assistant_message": assistant_message, "rf_code": rf_code_result}

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
            return assistant_message, _strip_code_fences(rf_content)

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
