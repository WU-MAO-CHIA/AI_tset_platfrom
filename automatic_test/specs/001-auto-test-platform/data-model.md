# Data Model: 自動化測試平台

**Phase**: 1 | **Date**: 2026-05-19 | **Plan**: [plan.md](./plan.md)

## Entity Relationship Overview

```
TestCase ──< TestData                (1 案例 → N 筆測試資料)
TestCase ──< MediaAttachment         (1 案例 → N 媒體附件)
TestCase ──< AutomationCode          (1 案例 → N 版本代碼)
TestChecklist ──< ChecklistItem      (1 清單 → N 案例項目)
ChecklistItem >── TestCase           (M 清單可引用同 1 案例)
TestChecklist ──< ExecutionRecord    (1 清單 → N 執行紀錄)
ExecutionRecord ──< CaseResult       (1 執行 → N 案例結果)
CaseResult ──< ExecutionMedia        (1 案例結果 → N 截圖/影片)
DBConnection ──< TestData            (1 連線 → N 撈取的測試資料，可選)
```

---

## Entity: TestCase（測試案例）

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| id | UUID | PK, NOT NULL | 主鍵 |
| case_number | VARCHAR(50) | UNIQUE, NOT NULL | 編號（使用者定義，唯一） |
| name | VARCHAR(200) | NOT NULL | 測試案例名稱 |
| description | TEXT | nullable | 測試案例說明 |
| precondition_steps | TEXT | nullable | 前置步驟（自然語言） |
| main_steps | TEXT | NOT NULL | 主要步驟（自然語言，AI 補齊/代碼生成來源） |
| system_category | VARCHAR(100) | NOT NULL | 系統別（篩選用） |
| tags | JSON | default=[] | 標籤列表 |
| version | INTEGER | NOT NULL, default=1 | 版本號（每次儲存自動遞增） |
| created_by | VARCHAR(100) | NOT NULL | 建立人員 |
| modified_by | VARCHAR(100) | nullable | 最後修改人員 |
| is_deleted | BOOLEAN | NOT NULL, default=False | 軟刪除標記 |
| created_at | DATETIME | NOT NULL | 建立時間 |
| updated_at | DATETIME | NOT NULL | 最後更新時間 |

**Validation Rules**:
- `case_number` 唯一性驗證（含軟刪除案例）；重複時回傳 409 Conflict
- `main_steps` 不可為空白
- 每次 UPDATE 自動遞增 `version`，記錄 `modified_by`
- 軟刪除：`is_deleted=True`，清單不再顯示，但歷史報告仍可查閱

---

## Entity: TestData（測試資料）

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| id | UUID | PK, NOT NULL | 主鍵 |
| test_case_id | UUID | FK(TestCase.id), NOT NULL | 所屬測試案例 |
| field_name | VARCHAR(100) | NOT NULL | 測試資料欄位名稱 |
| field_value | TEXT | nullable | 測試資料值 |
| source | ENUM | NOT NULL | 來源：`manual` / `db_import` / `file_import` |
| import_source_id | UUID | nullable | 若來自 DB 或檔案匯入，記錄來源 ID |
| row_index | INTEGER | NOT NULL | 排序序號 |
| created_at | DATETIME | NOT NULL | 建立時間 |

---

## Entity: MediaAttachment（媒體附件）

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| id | UUID | PK, NOT NULL | 主鍵 |
| test_case_id | UUID | FK(TestCase.id), NOT NULL | 所屬測試案例 |
| attachment_type | ENUM | NOT NULL | `image` / `video` / `url` |
| filename | VARCHAR(255) | nullable | 原始檔名（url 類型為 null） |
| file_path | VARCHAR(500) | nullable | 儲存路徑（url 類型為 null） |
| url | VARCHAR(2000) | nullable | 網址（非 url 類型為 null） |
| file_size_bytes | BIGINT | nullable | 檔案大小 |
| mime_type | VARCHAR(100) | nullable | MIME 類型 |
| created_at | DATETIME | NOT NULL | 上傳時間 |

**Validation Rules**:
- `image` 類型：file_size ≤10MB；允許 image/jpeg, image/png, image/gif, image/webp
- `video` 類型：file_size ≤100MB；允許 video/mp4, video/webm
- `url` 類型：需通過 URL 格式驗證（使用 `validators` 套件）

---

## Entity: AutomationCode（自動化測試代碼）

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| id | UUID | PK, NOT NULL | 主鍵 |
| test_case_id | UUID | FK(TestCase.id), NOT NULL | 所屬測試案例 |
| case_version | INTEGER | NOT NULL | 對應的測試案例版本號 |
| code_content | TEXT | NOT NULL | 生成的自動化測試代碼 |
| llm_model | VARCHAR(100) | NOT NULL | 生成使用的 LLM 模型名稱 |
| generation_status | ENUM | NOT NULL | `pending` / `generated` / `failed` |
| error_message | TEXT | nullable | 生成失敗時的錯誤訊息 |
| created_at | DATETIME | NOT NULL | 生成時間 |

**Unique Constraint**: `(test_case_id, case_version)` — 同版本只快取一份代碼

---

## Entity: TestChecklist（測試清單）

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| id | UUID | PK, NOT NULL | 主鍵 |
| name | VARCHAR(200) | NOT NULL | 清單名稱 |
| created_by | VARCHAR(100) | NOT NULL | 建立人員 |
| is_deleted | BOOLEAN | NOT NULL, default=False | 軟刪除 |
| created_at | DATETIME | NOT NULL | 建立時間 |
| updated_at | DATETIME | NOT NULL | 最後更新時間 |

---

## Entity: ChecklistItem（清單項目）

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| id | UUID | PK, NOT NULL | 主鍵 |
| checklist_id | UUID | FK(TestChecklist.id), NOT NULL | 所屬清單 |
| test_case_id | UUID | FK(TestCase.id), NOT NULL | 引用的測試案例 |
| position | INTEGER | NOT NULL | 排序序號 |
| created_at | DATETIME | NOT NULL | 加入時間 |

**Unique Constraint**: `(checklist_id, test_case_id)` — 同清單不重複引用同案例

---

## Entity: DBConnection（資料庫連線）

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| id | UUID | PK, NOT NULL | 主鍵 |
| name | VARCHAR(100) | NOT NULL | 連線顯示名稱 |
| db_type | ENUM | NOT NULL | 初期固定 `sqlite`，預留 `postgresql` / `mysql` |
| connection_string | TEXT | NOT NULL | 連線字串（敏感資料，加密儲存） |
| last_tested_at | DATETIME | nullable | 最後測試連線時間 |
| last_test_success | BOOLEAN | nullable | 最後測試是否成功 |
| created_at | DATETIME | NOT NULL | 建立時間 |

---

## Entity: ExecutionRecord（執行紀錄）

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| id | UUID | PK, NOT NULL | 主鍵 |
| checklist_id | UUID | FK(TestChecklist.id), NOT NULL | 所屬清單 |
| execution_type | ENUM | NOT NULL | `checklist` / `trial_run`（試跑） |
| status | ENUM | NOT NULL | `pending` / `running` / `completed` / `failed` / `cancelled` |
| executed_by | VARCHAR(100) | NOT NULL | 執行人員 |
| parallel_mode | BOOLEAN | NOT NULL, default=False | 是否使用平行執行 |
| max_workers | INTEGER | NOT NULL, default=5 | 最大並行數 |
| total_cases | INTEGER | NOT NULL | 案例總數 |
| passed_count | INTEGER | NOT NULL, default=0 | 通過數 |
| failed_count | INTEGER | NOT NULL, default=0 | 失敗數 |
| started_at | DATETIME | nullable | 開始時間 |
| finished_at | DATETIME | nullable | 完成時間 |
| result_dir | VARCHAR(500) | nullable | RF 結果目錄路徑 |
| created_at | DATETIME | NOT NULL | 建立時間 |

---

## Entity: CaseResult（案例執行結果）

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| id | UUID | PK, NOT NULL | 主鍵 |
| execution_id | UUID | FK(ExecutionRecord.id), NOT NULL | 所屬執行紀錄 |
| test_case_id | UUID | FK(TestCase.id), NOT NULL | 對應測試案例 |
| case_version | INTEGER | NOT NULL | 執行時使用的版本號 |
| automation_code_id | UUID | FK(AutomationCode.id), nullable | 使用的代碼版本 |
| status | ENUM | NOT NULL | `passed` / `failed` / `timeout` / `error` / `skipped` |
| elapsed_ms | INTEGER | nullable | 執行時間（毫秒） |
| failure_message | TEXT | nullable | 失敗訊息 |
| position | INTEGER | NOT NULL | 在清單中的順序 |
| created_at | DATETIME | NOT NULL | 建立時間 |

---

## Entity: ExecutionMedia（執行結果媒體）

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| id | UUID | PK, NOT NULL | 主鍵 |
| case_result_id | UUID | FK(CaseResult.id), NOT NULL | 所屬案例結果 |
| media_type | ENUM | NOT NULL | `screenshot` / `video` |
| file_path | VARCHAR(500) | NOT NULL | 儲存路徑（相對於 result_dir） |
| step_index | INTEGER | nullable | 對應的測試步驟順序 |
| step_name | VARCHAR(200) | nullable | 對應的步驟名稱 |
| created_at | DATETIME | NOT NULL | 擷取時間 |

---

## State Transitions

### TestCase.version
```
CREATE → version=1
SAVE (any field change) → version += 1
DELETE → is_deleted=True（版本不變）
```

### ExecutionRecord.status
```
CREATED → pending
START → running
ALL CASES DONE (all pass) → completed
ANY CASE FAILED → failed (execution continues)
USER CANCEL → cancelled
```

### CaseResult.status
```
QUEUED → (執行前)
RUNNING → 
  PASS → passed
  FAIL → failed
  TIMEOUT → timeout
  EXCEPTION → error
  SKIPPED (case deleted mid-run) → skipped
```

---

## Database Migration Strategy

- 使用 Alembic 管理 schema 版本
- 初期支援 SQLite；SQLAlchemy dialect 設計確保遷移至 PostgreSQL 只需更換 connection string
- 敏感欄位（`DBConnection.connection_string`）使用 SQLAlchemy-Utils 的 `EncryptedType` 加密儲存
