# REST API Contract: 自動化測試平台

**Phase**: 1 | **Date**: 2026-05-19 | **Base URL**: `/api/v1`

---

## Test Cases

### POST /cases
建立新測試案例

**Request Body**:
```json
{
  "case_number": "TC-001",
  "name": "登入功能測試",
  "description": "驗證使用者登入流程",
  "precondition_steps": "使用者已註冊帳號",
  "main_steps": "1. 開啟登入頁面\n2. 輸入帳號密碼\n3. 點擊登入按鈕\n4. 驗證進入首頁",
  "system_category": "auth",
  "tags": ["login", "smoke"],
  "created_by": "tester_01",
  "test_data": [
    { "field_name": "username", "field_value": "testuser@example.com" }
  ]
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "case_number": "TC-001",
  "version": 1,
  "created_at": "2026-05-19T10:00:00Z"
}
```

**Error**:
- `409 Conflict`: case_number 重複

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

### POST /cases/{case_id}/trial-run
立即試跑

**Response 202** (Accepted):
```json
{ "execution_id": "uuid", "stream_url": "/api/v1/executions/{id}/stream" }
```

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

### PUT /checklists/{checklist_id}/items
更新清單案例（覆寫 items 列表）

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
