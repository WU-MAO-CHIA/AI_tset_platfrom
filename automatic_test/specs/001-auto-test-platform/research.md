# Research: 自動化測試平台

**Phase**: 0 | **Date**: 2026-05-19 | **Plan**: [plan.md](./plan.md)

## 研究問題清單

1. LLM 多模型整合策略
2. Robot Framework 整合架構（代碼生成 + 執行 + 結果解析）
3. 媒體檔案儲存策略
4. 平行測試執行管理
5. 即時執行進度推送機制
6. Excel/CSV 測試參數解析

---

## 決策 1：LLM 多模型整合策略

**Decision**: 採用 Provider 抽象層（Protocol/ABC），初期實作 Anthropic（Claude）與 OpenAI 兩個 provider，透過設定檔切換。

**Rationale**:
- 規格要求「至少兩種主流 LLM 模型可切換」
- Provider 抽象層符合 SOLID 開放封閉原則（新增模型無需修改現有代碼）
- Anthropic SDK 與 OpenAI SDK 介面類似，抽象成本低

**Interface**:
```python
class LLMProvider(Protocol):
    async def complete(self, messages: list[dict], max_tokens: int) -> str: ...
    async def complete_with_vision(self, messages: list[dict], media: list[bytes]) -> str: ...
```

**兩項使用場景**:
1. **AI 步驟補齊**（`ai_service.complete_steps`）：傳入已填步驟 + 媒體附件 → 回傳補齊後的步驟文字
2. **AI 代碼生成**（`ai_service.generate_robot_code`）：傳入完整測試步驟 → 回傳 Robot Framework `.robot` 文字

**Prompt 設計**:
- 步驟補齊：System prompt 描述角色為「QA 測試步驟補充助理」，few-shot 示範典型步驟格式
- 代碼生成：System prompt 包含 Robot Framework 語法規範 + 所有可用 Library（Browser Library、Playwright）

**Alternatives considered**:
- 單一固定模型：不符合規格「至少兩種可切換」
- LangChain 抽象：過重，不符 YAGNI；直接 SDK 呼叫更輕量可控

---

## 決策 2：Robot Framework 整合架構

**Decision**: 以 subprocess 呼叫 `robot` CLI 執行 `.robot` 檔，執行前先由 `ai_service.generate_robot_code()` 生成檔案，執行後解析 `output.xml`。

**架構流程**:
```
測試案例（自然語言步驟）
    │
    ▼
ai_service.generate_robot_code()
    │
    ▼
.robot 檔案（存放於 robot_scripts/generated/{case_id}_{version}.robot）
    │
    ▼
execution_service.run_case() → subprocess.run(["robot", "--outputdir", ..., case.robot])
    │
    ▼
robot_scripts/results/{execution_id}/
    ├── output.xml
    ├── log.html
    ├── report.html
    └── screenshots/*.png / videos/*.mp4
    │
    ▼
report_service.parse_xml(output.xml) → ExecutionRecord + TestReport 寫入 DB
```

**Robot Framework Library 選擇**:
- `robotframework-browser` (Playwright-based)：支援截圖、影片錄製，現代化選擇
- 截圖：RF Browser 的 `Take Screenshot` 關鍵字（每個步驟可自動截圖）
- 影片錄製：RF Browser 的 `New Context` 設定 `record_video=True`

**XML 解析**:
- 使用 Python 內建 `xml.etree.ElementTree` 解析 `output.xml`
- 關鍵結構：`<suite>` → `<test>` → `<kw>` → `<status>`
- 擷取：每個 test 的 status（PASS/FAIL）、elapsedtime、message（失敗訊息）
- 截圖路徑從 XML `<msg>` 或 `<tag>` 中提取

**代碼快取策略**:
- 相同 `case_id + version` 的 .robot 檔若已存在則跳過生成（避免重複 LLM 呼叫）
- 案例版本遞增時清除舊快取並重新生成

**Alternatives considered**:
- `robotframework-selenium`：較舊，不支援原生影片錄製
- 直接呼叫 Playwright Python：繞過 RF，失去 RF 關鍵字結構與 XML 報告

---

## 決策 3：媒體檔案儲存策略

**Decision**: 本地檔案系統（設定化路徑），分三類目錄管理。

**目錄結構**:
```
{MEDIA_ROOT}/
├── attachments/             # 建立測試案例時上傳的圖片/影片/網址快取
│   └── {case_id}/
│       ├── {filename}
│       └── ...
└── execution_results/       # 測試執行過程中擷取的截圖/影片
    └── {execution_id}/
        ├── screenshots/
        └── videos/
```

**DB 中只存路徑，不存 Blob**（符合 KISS 原則）。

**API 服務**:
- `GET /media/attachments/{case_id}/{filename}` → 串流回應
- `GET /media/results/{execution_id}/{type}/{filename}` → 截圖直接回傳；影片使用 HTTP Range request 串流

**大小限制**（在 FastAPI middleware 層驗證）:
- 圖片：≤10MB，允許 .jpg/.png/.gif/.webp
- 影片：≤100MB，允許 .mp4/.webm
- 網址：僅驗證格式，不下載

**Alternatives considered**:
- S3/MinIO：過重，初期本地存取即可，介面已抽象，未來可替換
- DB Blob：性能差，備份複雜

---

## 決策 4：平行測試執行管理

**Decision**: 使用 Python `asyncio.Semaphore` 控制並行數，搭配 `asyncio.create_task` 非同步啟動各案例的 subprocess 執行。

**架構**:
```python
async def run_checklist_parallel(checklist_id, max_workers=5):
    semaphore = asyncio.Semaphore(max_workers)
    tasks = [run_case_with_semaphore(case, semaphore) for case in checklist.cases]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

**執行狀態管理**:
- `ExecutionRecord` 有 `status` 欄位：`pending | running | passed | failed | timeout | error`
- 每個案例執行時更新 DB 狀態（透過 async DB session）
- WebSocket 訂閱者在狀態變更時收到推送

**逾時處理**:
- 每個案例執行設定 `asyncio.wait_for(..., timeout=300)` (5分鐘)
- 逾時 → 終止 subprocess（`process.kill()`）→ 標記 `timeout`

**Alternatives considered**:
- `concurrent.futures.ThreadPoolExecutor`：不與 async FastAPI 整合，需額外橋接
- Celery：過重，初期不需要 broker；若未來需要分散式執行可引入

---

## 決策 5：即時執行進度推送機制

**Decision**: Server-Sent Events (SSE) — 比 WebSocket 更輕量，符合「只需單向推送」的場景。

**FastAPI SSE 實作**:
```python
@router.get("/executions/{execution_id}/stream")
async def stream_execution(execution_id: str):
    async def event_generator():
        while True:
            status = await get_execution_status(execution_id)
            yield f"data: {status.model_dump_json()}\n\n"
            if status.is_terminal:
                break
            await asyncio.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**前端**:
```typescript
const evtSource = new EventSource(`/api/executions/${id}/stream`)
evtSource.onmessage = (e) => store.updateProgress(JSON.parse(e.data))
```

**Alternatives considered**:
- WebSocket：雙向通訊，適合聊天應用；這裡只需服務端推送，SSE 夠用且更簡單
- Polling：每秒 GET 請求，效率低且產生大量無效請求

---

## 決策 6：Excel/CSV 測試參數解析

**Decision**: 使用 `openpyxl`（Excel）+ 內建 `csv` 模組（CSV）+ 自訂 Tab-分隔解析（文字檔），統一轉換為 `list[dict]` 結構。

**解析流程**:
1. 讀取上傳檔案的第一列為標頭（欄位名）
2. 與測試案例的測試資料欄位名稱做模糊比對（降低大小寫、去空白）
3. 回傳預覽資料（前 10 列）供使用者確認
4. 使用者確認後，逐列寫入 `TestData` 記錄

**欄位對應邏輯**:
- 精確比對：標頭名 == 測試資料欄位名 → 直接對應
- 模糊比對：`difflib.SequenceMatcher` 相似度 ≥0.8 → 提示使用者確認
- 無法對應 → 提示標頭名並請使用者手動選擇目標欄位

**Alternatives considered**:
- `pandas`：功能過重，僅需簡單解析；openpyxl + csv 足夠且依賴更輕

---

---

## 決策 7：測試案例編號自動生成策略（Session 2026-06-13）

**Decision**: 後端在建立測試案例時，根據 `system_category` 查詢**同前綴的最大現有序號**（含已軟刪除者以防 reuse），加 1 後格式化為三位數，組合為 `{system_category}-{NNN}`。若 `system_category` 為空則使用預設前綴 `TC`。

**Rationale**:
- 符合 spec：「編號由系統別+三位數序號組成，序號從 001 開始往後遞增，在同一系統別內保持唯一性」（Clarifications Session 2026-06-13）
- 查詢含軟刪除案例的最大號碼，防止刪除後重複使用
- 不依賴 DB auto-increment，因為編號前綴與 system_category 繫結

**Implementation sketch**:
```python
# In CaseService.generate_case_number()
async def generate_case_number(self, system_category: str) -> str:
    prefix = (system_category or "TC").strip()
    # Query all (including soft-deleted) to avoid reuse
    cases = await self.repo.list_by_prefix(prefix)
    max_num = 0
    for c in cases:
        parts = c.case_number.rsplit("-", 1)
        if len(parts) == 2 and parts[-1].isdigit():
            max_num = max(max_num, int(parts[-1]))
    return f"{prefix}-{str(max_num + 1).zfill(3)}"
```

**Alternatives considered**:
- DB sequence per system_category：需額外表格，過度複雜
- UUID：不符合 spec 要求
- Client-side generation：並行操作有競態條件風險

---

## 所有 NEEDS CLARIFICATION 解析完畢

| 問題 | 決策 |
|------|------|
| LLM 多模型 | Provider 抽象層，初期 Anthropic + OpenAI |
| RF 整合 | subprocess 呼叫 + XML 解析 + RF Browser |
| 媒體儲存 | 本地檔案系統，路徑設定化 |
| 平行執行 | asyncio.Semaphore，預設 5 並行 |
| 即時進度 | Server-Sent Events (SSE) |
| Excel/CSV | openpyxl + csv，標頭比對 + 預覽確認 |
| 案例編號生成 | system_category 前綴 + 三位數序號，查最大值+1 |
