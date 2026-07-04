# REST API Contract: 自動化測試平台

**Phase**: 1 | **Date**: 2026-05-19 | **Base URL**: `/api/v1`

---

## Test Cases

### POST /cases
建立新測試案例

> **Note**: `case_number` 由後端根據 `system_category` 自動生成（格式：`{system_category}-{NNN}`，序號含軟刪除案例以防重複）。請求中不需傳入 `case_number`。

**Request Body**:
```json
{
  "name": "登入功能測試",
  "description": "驗證使用者登入流程",
  "precondition_steps": "使用者已註冊帳號",
  "main_steps": "1. 開啟登入頁面\n2. 輸入帳號密碼\n3. 點擊登入按鈕\n4. 驗證進入首頁",
  "system_category": "auth",
  "tags": ["login", "smoke"],
  "created_by": "tester_01",
  "test_data": [
    {
      "field_name": "username",
      "rf_variable": "${username}",
      "field_value": "testuser@example.com",
      "description": "登入帳號"
    }
  ]
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "case_number": "auth-001",
  "version": 1,
  "created_at": "2026-05-19T10:00:00Z"
}
```

---

### GET /cases
取得測試案例清單（支援篩選）

**Query Parameters**:
| 參數 | 型別 | 說明 |
|------|------|------|
| system_category | string | 篩選系統別 |
| keyword | string | 名稱關鍵字模糊搜尋 |
| tags | string[] | 標籤篩選（逗號分隔） |
| page | int | 分頁（預設 1） |
| page_size | int | 每頁筆數（預設 20，最大 100） |

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "case_number": "TC-001",
      "name": "登入功能測試",
      "system_category": "auth",
      "tags": ["login"],
      "version": 1,
      "created_by": "tester_01",
      "updated_at": "2026-05-19T10:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20
}
```

---

### GET /cases/{case_id}
取得測試案例詳細資料

**Response 200**: 完整 TestCase 物件（含 test_data、attachments、version_history 摘要）

---

### GET /cases/{case_id}/execution-history
取得測試案例的執行歷史（曾被哪些 ExecutionRecord 執行過）

**Query Parameters**:
| 參數 | 型別 | 說明 |
|------|------|------|
| page | int | 分頁（預設 1） |
| page_size | int | 每頁筆數（預設 20） |

**Response 200**:
```json
{
  "items": [
    {
      "execution_id": "uuid",
      "status": "completed",
      "started_at": "2026-05-19T10:00:00Z",
      "finished_at": "2026-05-19T10:02:00Z",
      "passed_count": 1,
      "failed_count": 0,
      "checklist_name": "Sprint 1 測試"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

**Error**:
- `404 Not Found`: 案例不存在

---

### PUT /cases/{case_id}
更新測試案例（自動遞增版本號）

**Request Body**: 同 POST，但不包含 `case_number`（編號不可修改）
**Response 200**: 更新後的完整案例物件（含新版本號）

---

### DELETE /cases/{case_id}
軟刪除測試案例

**Request Body**:
```json
{ "deleted_by": "tester_01" }
```

**Response 200**: `{ "success": true }`
**Error**:
- `409 Conflict`: 案例正被進行中的執行使用
  ```json
  { "error": "case_in_use", "active_executions": ["exec_uuid_1"] }
  ```

---

### POST /cases/{case_id}/ai-complete
AI 輔助補齊測試步驟

**Request Body**:
```json
{
  "partial_steps": "1. 開啟登入頁面\n2. 輸入...",
  "llm_model": "claude-3-5-sonnet",
  "description": "驗證登入流程"
}
```

**Response 200**:
```json
{
  "completed_steps": "1. 開啟登入頁面\n2. 輸入帳號密碼\n3. 點擊登入按鈕\n4. 驗證顯示首頁",
  "model_used": "claude-3-5-sonnet"
}
```

---

### POST /cases/{case_id}/attachments
上傳媒體附件

**Request**: `multipart/form-data`，欄位 `file`（binary）或 `url`（string）
**Response 201**:
```json
{
  "id": "uuid",
  "attachment_type": "image",
  "filename": "screenshot.png",
  "file_size_bytes": 102400
}
```

**Error**:
- `413 Payload Too Large`: 超過大小限制

---

### POST /cases/{case_id}/import-test-data
匯入 Excel/CSV 測試參數（預覽模式）

**Request**: `multipart/form-data`，欄位 `file`
**Response 200**:
```json
{
  "preview": [
    { "username": "user1@example.com", "password": "pass1" },
    { "username": "user2@example.com", "password": "pass2" }
  ],
  "total_rows": 50,
  "columns": ["username", "password"],
  "warnings": []
}
```

---

### POST /cases/{case_id}/import-test-data/confirm
確認匯入測試資料

**Request Body**: `{ "import_token": "..." }` （上一步回傳）
**Response 201**: `{ "imported_count": 50 }`

---

### POST /cases/{case_id}/chat
多輪 AI 對話，生成 RF 程式碼（Tab 2 Chat 介面）

**Request Body**:
```json
{
  "message": "請幫我生成登入功能的測試腳本",
  "llm_model": "claude-sonnet-4-6"
}
```

**Response 200**:
```json
{
  "assistant_message": "好的，以下是登入功能的 Robot Framework 腳本...",
  "rf_code": "*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\n登入功能測試\n    Open Browser..."
}
```

**Side effect**: 用戶訊息與 AI 回應均寫入 `case_chat_messages` 表持久化

**Note**: `assistant_message` 僅包含人類可讀部分（RF code 已從 content 提取）

---

### GET /cases/{case_id}/chat-history
取得測試案例的 AI 對話歷史（含試跑結果）— Phase 27 擴充

**Response 200**:
```json
{
  "messages": [
    {
      "id": "msg_uuid_1",
      "type": "chat",
      "role": "user",
      "content": "請幫我生成登入功能的測試腳本",
      "created_at": "2026-06-13T10:00:00Z"
    },
    {
      "id": "msg_uuid_2",
      "type": "chat",
      "role": "assistant",
      "content": "好的，以下是登入功能的 Robot Framework 腳本...\n---RF_CODE---\n*** Settings ***\n...\n---END---",
      "created_at": "2026-06-13T10:00:05Z"
    },
    {
      "id": "msg_uuid_3",
      "type": "trial_run_result",
      "role": "system",
      "content": {
        "status": "failed",
        "elapsed_ms": 5234,
        "error_message": "步驟 'Login' 失敗：登入逾時",
        "screenshot_paths": ["executions/abc123/screenshots/step_1.png", "executions/abc123/screenshots/step_2.png"]
      },
      "created_at": "2026-06-13T10:01:30Z"
    },
    {
      "id": "msg_uuid_4",
      "type": "chat",
      "role": "assistant",
      "content": "我分析了試跑失敗的原因。登入超時通常是因為頁面載入過慢或元素選擇器不準確...\n---RF_CODE---\n*** Settings ***\n...\n---END---",
      "created_at": "2026-06-13T10:01:35Z"
    }
  ]
}
```

**Mesage 物件結構**:
- `id`：訊息唯一 ID
- `type`：訊息型別（`chat` 或 `trial_run_result`）
- `role`：發送者角色
  - `chat` 型別：`user` / `assistant`
  - `trial_run_result` 型別：`system`
- `content`：訊息內容
  - `chat` 型別：字串（包含 `---RF_CODE---` 分隔符）
  - `trial_run_result` 型別：JSON 物件（status、elapsed_ms、error_message、screenshot_paths）
- `created_at`：建立時間

**前端解析規則**:
- `type='chat'`：按原有邏輯解析（`role=user` 為使用者氣泡，`role=assistant` 為 AI 氣泡，提取 RF code）
- `type='trial_run_result'`：解析 JSON content，顯示 badge（綠色 PASS / 紅色 FAIL）+ 執行時間，展開區域顯示錯誤訊息與截圖廊道

**Note**: Phase 27 前的訊息自動補全 `type='chat'`，確保向後相容性

---

### POST /cases/preview-rf
根據測試步驟預覽生成 RF 代碼（不建立案例）

**Request Body**:
```json
{ "main_steps": "1. 開啟登入頁面\n2. 輸入帳號密碼", "llm_model": "claude-sonnet-4-6" }
```

**Response 200**: `{ "rf_code": "*** Settings ***\n..." }`

---

### POST /cases/{case_id}/trial-run
立即試跑（Tab 2 按鈕）— Phase 27 擴充

使用右側 RF 程式碼預覽區的當前內容執行試跑，無需先儲存案例。完成後將結果以 `type: "trial_run_result"` 訊息附加至左側 Chat，並自動觸發 AI 分析失敗原因（若失敗）。

**Request Body** (Phase 27 新增):
```json
{
  "rf_code": "*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\n登入測試\n    ...",
  "case_name": "登入功能測試"
}
```
> `rf_code`：右側預覽區當前的 RF 程式碼文字（必填）
> `case_name`：用於錯誤訊息與 AI 分析的案例名稱（選填，若省略使用 case_id）

**Response 202** (Accepted):
```json
{ "execution_id": "uuid", "stream_url": "/api/v1/executions/{id}/stream" }
```

**試跑完成後自動流程**:
1. 後端解析 RF 執行結果，生成 `trial_run_result` 訊息：
   ```json
   {
     "type": "trial_run_result",
     "role": "system",
     "content": {
       "status": "failed",
       "elapsed_ms": 5234,
       "error_message": "步驟 'Login' 失敗：登入逾時",
       "screenshot_paths": ["executions/abc123/screenshots/step_1.png"]
     }
   }
   ```
2. 自動建立該訊息至 `case_chat_messages`（`type='trial_run_result'`）
3. 若 `status='failed'`，自動觸發 AI 分析，組裝 prompt 並調用 AI 服務
4. AI 回應附加為新的 `ChatMessage`（`type='chat'`，`role='assistant'`）
5. 前端 SSE 推送兩條訊息給客戶端

**Error**:
- `404 Not Found`: 案例不存在
- `422 Unprocessable Entity`: 請求體格式錯誤（如 rf_code 為空）

---

## Test Checklists

### POST /checklists
建立測試清單

**Request Body**:
```json
{
  "name": "Sprint 5 回歸測試",
  "created_by": "tester_01",
  "case_ids": ["uuid1", "uuid2", "uuid3"]
}
```
**Response 201**: 完整 TestChecklist 物件

---

### GET /checklists
取得清單列表（支援名稱篩選、分頁）

### GET /checklists/{checklist_id}
取得清單詳細（含 items 和 execution_history 摘要）

**Response 200**:
```json
{
  "id": "uuid",
  "name": "Sprint 5 回歸測試",
  "created_by": "tester_01",
  "items": [
    { "id": "uuid", "test_case_id": "uuid", "case_number": "auth-001", "name": "登入功能測試", "position": 1, "notes": null }
  ],
  "execution_history": [
    { "execution_id": "uuid", "status": "completed", "started_at": "...", "passed_count": 3, "failed_count": 0 }
  ]
}
```

---

### PUT /checklists/{checklist_id}
編輯清單基本資訊（名稱、建立人員）

**Request Body**:
```json
{ "name": "Sprint 5 完整回歸測試", "created_by": "tester_02" }
```
**Response 200**: 更新後完整 TestChecklist 物件

---

### DELETE /checklists/{checklist_id}
刪除測試清單

**Response 200**: `{ "success": true }`

**Error**:
- `409 Conflict`: 清單有執行中的測試
  ```json
  { "error": "checklist_in_use", "active_executions": ["exec_uuid_1"] }
  ```

---

### GET /checklists/{checklist_id}/cases
取得案例管理畫面的案例列表（含備註、排序、測資變數、實際值）

**Response 200**:
```json
{
  "items": [
    {
      "item_id": "uuid",
      "test_case_id": "uuid",
      "case_number": "auth-001",
      "name": "登入功能測試",
      "position": 1,
      "notes": "此清單專用備註",
      "actual_values": { "${username}": "real_user_001" },
      "test_data": [
        {
          "id": "uuid",
          "field_name": "username",
          "rf_variable": "${username}",
          "field_value": "testuser@example.com",
          "description": "登入帳號",
          "row_index": 0
        }
      ]
    }
  ],
  "total": 3
}
```

> **Phase 25 新增**: `test_data` 陣列（含 4 欄：field_name、rf_variable、field_value、description）與 `actual_values` JSON 物件（ChecklistItem 層級覆寫值）。
```

---

### POST /checklists/{checklist_id}/cases
新增案例至清單

**Request Body**:
```json
{ "case_id": "uuid", "position": null }
```
> `position` 為 null 時加入末尾

**Response 201**:
```json
{ "item_id": "uuid", "position": 4 }
```

**Error**:
- `409 Conflict`: 案例已在清單中

---

### DELETE /checklists/{checklist_id}/cases/{case_id}
從清單移除案例

**Response 200**: `{ "success": true }`

---

### PATCH /checklists/{checklist_id}/cases/{case_id}
更新清單項目屬性（備註、排序或實際測試值）

**Request Body** (所有欄位均為 optional):
```json
{
  "notes": "此案例在此清單中的備註",
  "position": 2,
  "actual_values": { "${username}": "real_user_001", "${password}": "RealPass123" }
}
```
> **Phase 25 新增**: `actual_values`（object）持久化至 ChecklistItem；執行時優先套用，有值時取代案例的 field_value；送入 `null` 時清除。

**Response 200**: 更新後的 ChecklistItem 物件（含 `actual_values`）

---

### PUT /checklists/{checklist_id}/cases/reorder
批次更新排序（拖曳後送出完整新順序）

**Request Body**:
```json
{ "case_ids": ["uuid3", "uuid1", "uuid2"] }
```
> 列表順序即為新的 position 1, 2, 3...

**Response 200**: `{ "success": true }`

---

### PUT /checklists/{checklist_id}/items
更新清單案例（覆寫 items 列表，舊介面保留相容）

**Request Body**: `{ "case_ids": ["uuid1", "uuid3"] }`

---

### POST /checklists/{checklist_id}/execute
執行測試清單

**Request Body**:
```json
{
  "executed_by": "tester_01",
  "parallel_mode": true,
  "max_workers": 5
}
```
**Response 202**:
```json
{ "execution_id": "uuid", "stream_url": "/api/v1/executions/{id}/stream" }
```

---

## Executions

### GET /executions/{execution_id}
取得執行紀錄（含所有 CaseResult 摘要）

### GET /executions/{execution_id}/results
取得詳細結果（含 ExecutionMedia 列表）

**Response 200**:
```json
{
  "execution_id": "uuid",
  "status": "completed",
  "started_at": "...",
  "finished_at": "...",
  "case_results": [
    {
      "id": "uuid",
      "test_case_id": "uuid",
      "case_number": "TC-001",
      "name": "登入功能測試",
      "status": "passed",
      "elapsed_ms": 3200,
      "failure_message": null,
      "media": [
        {
          "id": "uuid",
          "media_type": "screenshot",
          "url": "/api/v1/media/results/exec_id/screenshots/step1.png",
          "step_index": 3,
          "step_name": "驗證顯示首頁"
        }
      ]
    }
  ]
}
```

### GET /executions/{execution_id}/export
匯出測試報告為可下載 HTML 檔案（對應 FR-011）

**Response 200**:
- `Content-Type: text/html; charset=utf-8`
- `Content-Disposition: attachment; filename="report_{execution_id}.html"`
- Body: 完整 HTML 報告（含每個案例結果、執行時間、失敗詳情）

**Error**:
- `404 Not Found`: 執行紀錄不存在
- `422 Unprocessable Entity`: 執行尚未完成，報告無法產生

---

### GET /executions/{execution_id}/rf-report/{filename}
取得 RF 原生執行報告檔案（對應 FR-010 / FR-019 嵌入報告）

`{filename}` 可為 `log.html`、`report.html`、`output.xml` 或其他 RF 生成的靜態資產。

**Response 200**:
- `Content-Type: text/html; charset=utf-8`（`.html`）或依副檔名推斷
- Body: RF 原生檔案內容（由 `data/execution_reports/{execution_id}/{filename}` 服務）

**使用場景**:
- 前端 ResultPage.vue「RF 報告」Tab 的 `<iframe>` src
  ```html
  <iframe :src="`/api/v1/executions/${executionId}/rf-report/log.html`" />
  <iframe :src="`/api/v1/executions/${executionId}/rf-report/report.html`" />
  ```
- 子 Tab 切換：「執行日誌（log.html）」/ 「測試報告（report.html）」

**Error**:
- `404 Not Found`: 執行紀錄不存在或報告尚未生成（執行仍在進行中）

**注意**: 此端點服務 RF 原生報告，與 `/export`（FR-011 Jinja2 自製報告）為不同功能，不可混淆。

---

### GET /executions/{execution_id}/stream
SSE 即時執行進度串流

**Response**: `text/event-stream`
```
data: {"execution_id":"uuid","status":"running","total":5,"completed":2,"running_cases":["TC-003"]}

data: {"execution_id":"uuid","status":"running","total":5,"completed":3,"running_cases":["TC-004","TC-005"]}

data: {"execution_id":"uuid","status":"completed","total":5,"passed":4,"failed":1}
```

---

## DB Connections

### POST /db-connections
建立資料庫連線設定

### POST /db-connections/{connection_id}/test
測試連線

**Response 200**: `{ "success": true, "latency_ms": 45 }`
**Response 200** (failure): `{ "success": false, "error": "Connection refused" }`

### POST /db-connections/{connection_id}/query
執行查詢撈取測試資料

**Request Body**:
```json
{ "query": "SELECT username, password FROM test_users LIMIT 10" }
```

**Response 200**:
```json
{
  "columns": ["username", "password"],
  "rows": [["user1@example.com", "pass1"], ...],
  "row_count": 10
}
```

---

## Media

### GET /media/attachments/{case_id}/{filename}
取得媒體附件（截圖/影片串流）

### GET /media/results/{execution_id}/screenshots/{filename}
取得執行截圖

### GET /media/results/{execution_id}/videos/{filename}
取得執行影片（支援 HTTP Range request 串流）

---

## LLM Models

### GET /llm-models
取得可用 LLM 模型列表

**Response 200**:
```json
{
  "models": [
    { "id": "claude-3-5-sonnet", "display_name": "Claude 3.5 Sonnet", "provider": "anthropic" },
    { "id": "gpt-4o", "display_name": "GPT-4o", "provider": "openai" }
  ]
}
```

---

## Error Response Format

所有錯誤統一格式：
```json
{
  "error": "error_code",
  "message": "人類可讀的錯誤訊息",
  "details": {}
}
```

| HTTP Code | 說明 |
|-----------|------|
| 400 | 請求格式錯誤或驗證失敗 |
| 404 | 資源不存在 |
| 409 | 資源衝突（如編號重複、刪除鎖定） |
| 413 | 上傳檔案超過大小限制 |
| 422 | 業務邏輯驗證失敗 |
| 500 | 伺服器內部錯誤 |
| 503 | 外部服務不可用（LLM API、外部 DB） |
