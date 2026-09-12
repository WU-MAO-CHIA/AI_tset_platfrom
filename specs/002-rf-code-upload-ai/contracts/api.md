# API Contracts: RF Code Upload and AI Integration

**Feature**: RF Code Upload and AI Integration  
**Date**: 2026-09-10  
**Base URL**: `/api/v1`

---

## 1. Upload RF Script File

Upload a Robot Framework (.robot) file for a test case.

### Endpoint
```
POST /cases/{case_id}/robot-script/upload
```

### Authentication
- Required: Bearer token (editor role or above)
- Header: `Authorization: Bearer <token>`

### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| case_id | string (UUID) | Yes | Test case identifier |

### Request
**Content-Type**: `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | file | Yes | .robot file (max 500KB) |

### Validations
- File extension must be `.robot` (case-insensitive)
- File size must not exceed 500KB
- File content must be valid UTF-8 (fallback: utf-8-sig, big5, gbk)
- Test case must exist and not be soft-deleted
- User must have editor role or above

### Responses

#### Success (200 OK)
```json
{
  "rf_code": "*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\n登入測試\n    [Documentation]    測試登入功能\n    [Tags]    login\n    Open Test Browser\n    Fill Text    role=textbox[name=\"帳號\"]    test_user\n    Fill Text    role=textbox[name=\"密碼\"]    test_pass\n    Click    role=button[name=\"登入\"]\n    Get Text    role=heading    ==    歡迎",
  "case_number": "TC-001",
  "file_path": "/path/to/robot_scripts/TC-001.robot",
  "size_bytes": 1024,
  "encoding": "utf-8"
}
```

#### Error Responses

**400 Bad Request - Invalid Extension**
```json
{
  "error": "invalid_extension",
  "message": "只接受 .robot 檔案"
}
```

**400 Bad Request - Encoding Error**
```json
{
  "error": "encoding_error",
  "message": "無法解碼檔案內容，請確認檔案為 UTF-8 編碼"
}
```

**403 Forbidden - Insufficient Permissions**
```json
{
  "detail": "權限不足"
}
```

**404 Not Found - Case Not Found**
```json
{
  "error": "not_found",
  "message": "案例不存在"
}
```

**413 Payload Too Large**
```json
{
  "error": "file_too_large",
  "message": "檔案超過 500KB 限制"
}
```

---

## 2. Save RF Script (Existing - Extended)

Save or update RF code for a test case (used after editing in Monaco Editor).

### Endpoint
```
PUT /cases/{case_id}/robot-script
```

### Request
**Content-Type**: `application/json`

```json
{
  "rf_code": "*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\n登入測試\n    [Documentation]    測試登入功能\n    [Tags]    login\n    Open Test Browser\n    Fill Text    role=textbox[name=\"帳號\"]    test_user\n    Fill Text    role=textbox[name=\"密碼\"]    test_pass\n    Click    role=button[name=\"登入\"]\n    Get Text    role=heading    ==    歡迎"
}
```

### Response (200 OK)
```json
{
  "case_number": "TC-001",
  "file_path": "/path/to/robot_scripts/TC-001.robot"
}
```

---

## 3. Get RF Script (Existing)

Retrieve saved RF code for a test case.

### Endpoint
```
GET /cases/{case_id}/robot-script
```

### Response (200 OK)
```json
{
  "rf_code": "*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\n登入測試\n    [Documentation]    測試登入功能\n    [Tags]    login\n    Open Test Browser\n    Fill Text    role=textbox[name=\"帳號\"]    test_user\n    Fill Text    role=textbox[name=\"密碼\"]    test_pass\n    Click    role=button[name=\"登入\"]\n    Get Text    role=heading    ==    歡迎",
  "case_number": "TC-001",
  "source": "db"
}
```

**source values**: `"db"` (from database), `"file"` (from disk fallback)

---

## 4. AI Chat with RF Context (Extended)

Chat with AI assistant, optionally including RF code as context.

### Endpoint
```
POST /cases/{case_id}/chat
```

### Request
**Content-Type**: `application/json`

```json
{
  "message": "這段 RF 代碼有什麼問題？",
  "llm_model": "claude-3-5-sonnet-20241022",
  "rf_context_mode": "full"
}
```

### Parameters
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| message | string | Yes | - | User message |
| llm_model | string | No | Default from settings | LLM model to use |
| rf_context_mode | string | No | "full" | Context scope: "full", "summary", "none" |

### Response (200 OK)
```json
{
  "assistant_message": "這段 RF 代碼整體結構良好，但有幾個建議：\n1. 缺少 Test Setup/Teardown 的錯誤處理\n2. 建議加入顯式等待而非依賴 auto-wait\n3. 選擇器建議使用 data-testid 屬性...",
  "rf_code": "*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\n登入測試\n    [Documentation]    測試登入功能\n    [Tags]    login\n    Open Test Browser\n    Fill Text    role=textbox[name=\"帳號\"]    test_user\n    Fill Text    role=textbox[name=\"密碼\"]    test_pass\n    Click    role=button[name=\"登入\"]\n    Get Text    role=heading    ==    歡迎"
}
```

### Behavior
- If `rf_context_mode` = "full": Full RF code injected in system prompt
- If `rf_context_mode` = "summary": AI-generated summary injected
- If `rf_context_mode` = "none": No RF context (standard chat)
- If case has no RF code: Works normally regardless of mode
- Response `rf_code` field echoes the context used (for UI confirmation)

---

## 5. Test Case Creation with RF Upload (Extended)

The existing `POST /cases` endpoint supports optional RF code in request body.

### Request Extension
```json
{
  "name": "登入功能測試",
  "main_steps": "1. 開啟登入頁面\n2. 輸入帳號密碼\n3. 點擊登入\n4. 驗證登入成功",
  "created_by": "test_user",
  "description": "測試登入流程",
  "system_category": "Web",
  "tags": ["login", "smoke"],
  "rf_code": "*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\n登入測試\n    [Documentation]    測試登入功能\n    [Tags]    login\n    Open Test Browser\n    Fill Text    role=textbox[name=\"帳號\"]    test_user\n    Fill Text    role=textbox[name=\"密碼\"]    test_pass\n    Click    role=button[name=\"登入\"]\n    Get Text    role=heading    ==    歡迎"
}
```

### Notes
- `rf_code` field is optional
- If provided, creates RobotScript record on case creation
- Multipart upload via `/robot-script/upload` is alternative for file-based workflow

---

## 6. Test Case Update with RF Code (Extended)

The existing `PUT /cases/{case_id}` endpoint supports optional `rf_code` field.

### Request Extension
```json
{
  "name": "登入功能測試 (更新)",
  "main_steps": "更新後的步驟...",
  "created_by": "test_user",
  "rf_code": "*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\n登入測試\n    [Documentation]    更新後的測試\n    [Tags]    login\n    Open Test Browser\n    ..."
}
```

### Behavior
- If `rf_code` provided: Updates RobotScript (overwrites per Q3=A)
- If `rf_code` = null/omitted: No change to existing RF code
- If `rf_code` = "" (empty string): Clears RF code (deletes RobotScript record)