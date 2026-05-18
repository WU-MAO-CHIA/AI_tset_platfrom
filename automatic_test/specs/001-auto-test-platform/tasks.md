# Tasks: 自動化測試平台 (Automatic Test Platform)

**Input**: Design documents from `/specs/001-auto-test-platform/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: 包含測試任務（Constitution III 強制 TDD — NON-NEGOTIABLE）。所有測試任務必須先寫並確認 FAIL，再開始實作。

**Organization**: 依 User Story 分組，每個 Story 為獨立可測試增量。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可平行執行（不同檔案，無未完成的相依）
- **[Story]**: 對應 User Story（US1–US5）
- TDD 順序：測試先寫（RED）→ 實作（GREEN）→ 重構（REFACTOR）

---

## Phase 1: Setup（專案初始化）

**Purpose**: 建立完整目錄結構與基礎設定檔

- [ ] T001 建立 backend 目錄結構：`backend/src/{models,repositories,services,api,core}/`、`backend/tests/{unit,integration,contract}/`
- [ ] T002 [P] 建立 frontend 目錄結構：`frontend/src/{components,pages,services,stores,types}/`、`frontend/tests/{unit,e2e}/`
- [ ] T003 [P] 建立 `robot_scripts/{generated,results}/` 目錄結構及 `.gitkeep`
- [ ] T004 建立 `backend/requirements.txt`（fastapi, uvicorn, sqlalchemy, alembic, python-multipart, aiofiles, httpx, openpyxl, robotframework, robotframework-browser, anthropic, openai, validators, sqlalchemy-utils）及 `backend/requirements-dev.txt`（pytest, pytest-asyncio, pytest-cov, httpx）
- [ ] T005 [P] 建立 `frontend/package.json`（vue 3, typescript, pinia, vue-router 4, axios, vueuse）及 `frontend/vite.config.ts`
- [ ] T006 建立 `backend/.env.example`（DATABASE_URL, MEDIA_ROOT, ROBOT_SCRIPTS_DIR, PARALLEL_MAX_WORKERS, ANTHROPIC_API_KEY, OPENAI_API_KEY, DEFAULT_LLM_MODEL）
- [ ] T007 [P] 建立 `backend/pytest.ini`（asyncio_mode=auto, testpaths=tests）及 `frontend/vitest.config.ts`
- [ ] T008 建立 `backend/alembic.ini` 及執行 `alembic init backend/alembic/`

**Checkpoint**: 執行 `cd backend && pip install -r requirements.txt` 和 `cd frontend && npm install` 均無錯誤

---

## Phase 2: Foundational（阻塞性前置基礎）

**Purpose**: 所有 User Story 依賴的核心基礎架構

**⚠️ CRITICAL**: 此 Phase 完成前，任何 User Story 均不可開始

- [ ] T009 建立 `backend/src/core/config.py`（pydantic-settings 讀取 .env，暴露 Settings singleton）
- [ ] T010 建立 `backend/src/core/database.py`（SQLAlchemy async engine + AsyncSessionLocal + get_db dependency）
- [ ] T011 [P] 建立 `backend/src/core/dependencies.py`（FastAPI dependency injection 工廠函式）
- [ ] T012 建立 `backend/src/models/base.py`（SQLAlchemy DeclarativeBase + TimestampMixin with created_at/updated_at）
- [ ] T013 建立 `backend/src/repositories/base.py`（Generic Repository ABC：get, list, create, update, delete）
- [ ] T014 [P] 建立 `backend/src/main.py`（FastAPI app 初始化、CORS、exception handlers、router 掛載）
- [ ] T015 建立 `backend/alembic/env.py`（設定 async migrations，import 所有 model）
- [ ] T016 建立 `frontend/src/main.ts`（Vue app 初始化、Pinia、Vue Router）
- [ ] T017 [P] 建立 `frontend/src/router/index.ts`（Vue Router 設定，預留所有頁面路由）
- [ ] T018 建立 `frontend/src/services/apiClient.ts`（Axios instance，統一 baseURL、interceptor、error handling）

**Checkpoint**: `uvicorn src.main:app` 啟動無錯誤；`npm run dev` 可存取 localhost:5173

---

## Phase 3: User Story 1 — 建立測試案例（Priority: P1）🎯 MVP

**Goal**: 測試人員可建立、編輯、刪除測試案例，含版本管理、AI 步驟補齊、多媒體附件上傳、立即試跑

**Independent Test**: `POST /api/v1/cases` 建立案例後出現於清單，版本號為 v1；AI 補齊回傳補充後的步驟；刪除後案例不再出現

### TDD 測試（先寫、確認 RED）

- [ ] T019 [P] [US1] 寫 contract test：`backend/tests/contract/test_cases_api.py`（POST /cases 201、case_number 重複 409、PUT /cases/{id} 版本遞增、DELETE /cases/{id} 軟刪除 200）
- [ ] T020 [P] [US1] 寫 unit test：`backend/tests/unit/test_case_service.py`（create、update 版本遞增、soft_delete、delete_blocked_by_execution）
- [ ] T021 [P] [US1] 寫 integration test：`backend/tests/integration/test_case_crud.py`（完整 CRUD with real SQLite）
- [ ] T022 [P] [US1] 寫 unit test：`backend/tests/unit/test_ai_service.py`（LLMProvider mock、complete_steps、provider 切換）
- [ ] T023 [P] [US1] 寫 unit test：`backend/tests/unit/test_media_service.py`（上傳驗證、大小限制、路徑生成）

### 實作

- [ ] T024 [P] [US1] 建立 `backend/src/models/test_case.py`（TestCase ORM：id, case_number, name, description, precondition_steps, main_steps, system_category, tags, version, created_by, modified_by, is_deleted, timestamps）
- [ ] T025 [P] [US1] 建立 `backend/src/models/test_data.py`（TestData ORM：id, test_case_id FK, field_name, field_value, source ENUM, row_index）
- [ ] T026 [P] [US1] 建立 `backend/src/models/media_attachment.py`（MediaAttachment ORM：id, test_case_id FK, attachment_type ENUM, filename, file_path, url, file_size_bytes, mime_type）
- [ ] T027 [US1] 執行 `alembic revision --autogenerate -m "add_test_case_tables"` 並驗證 migration 可正常 upgrade/downgrade
- [ ] T028 [US1] 建立 `backend/src/repositories/test_case_repo.py`（TestCaseRepository extends Generic Repo：soft_delete, list_with_filters, get_by_case_number, increment_version）
- [ ] T029 [US1] 建立 `backend/src/services/case_service.py`（CaseService：create, update 含版本遞增, soft_delete 含引用檢查, validate_case_number_unique）
- [ ] T030 [US1] 建立 `backend/src/services/media_service.py`（MediaService：upload_attachment, validate_file_type_and_size, serve_file, delete_attachment）
- [ ] T031 [P] [US1] 建立 `backend/src/core/llm_provider.py`（LLMProvider Protocol + AnthropicProvider + OpenAIProvider 實作，complete/complete_with_vision）
- [ ] T032 [US1] 建立 `backend/src/services/ai_service.py`（AIService：complete_steps, generate_robot_code 骨架，注入 LLMProvider）
- [ ] T033 [US1] 建立 `backend/src/api/cases.py`（FastAPI router：POST /cases、GET /cases/{id}、PUT /cases/{id}、DELETE /cases/{id}、POST /cases/{id}/ai-complete、POST /cases/{id}/attachments）
- [ ] T034 [US1] 建立 `frontend/src/services/caseApi.ts`（createCase, getCase, updateCase, deleteCase, aiComplete, uploadAttachment）
- [ ] T035 [US1] 建立 `frontend/src/stores/caseStore.ts`（Pinia store：currentCase, savingState, aiCompletionState）
- [ ] T036 [P] [US1] 建立 `frontend/src/components/TestCaseForm/index.vue`（表單：所有欄位輸入、TestData 動態新增、LLM 模型選擇、AI 補齊按鈕、媒體上傳區）
- [ ] T037 [P] [US1] 建立 `frontend/src/components/MediaUploader/index.vue`（圖片/影片上傳 + 網址輸入，含大小限制提示）
- [ ] T038 [US1] 建立 `frontend/src/pages/CaseCreatePage.vue`（組合 TestCaseForm，連接 caseStore，處理儲存/AI 補齊/試跑觸發）
- [ ] T039 [US1] 在 `frontend/src/components/TestCaseForm/index.vue` 加入「立即試跑」按鈕（呼叫 `POST /cases/{id}/trial-run`，顯示試跑進度）
- [ ] T040 [US1] 寫 frontend unit test：`frontend/tests/unit/TestCaseForm.spec.ts`（必填驗證、AI 補齊觸發、媒體上傳互動）

**Checkpoint**: 可用 `curl` 建立測試案例、AI 補齊成功回傳、媒體上傳至本地路徑

---

## Phase 4: User Story 2 — 瀏覽與篩選測試案例（Priority: P1）

**Goal**: 測試人員可多條件篩選案例清單、查看詳情（含版本歷史）、上傳 Excel/CSV 匯入測試參數、從案例查看執行歷史

**Independent Test**: 多條件篩選千筆案例 ≤2s；Excel 上傳後預覽正確；從案例詳情頁可看到執行歷史

### TDD 測試（先寫、確認 RED）

- [ ] T041 [P] [US2] 寫 contract test：`backend/tests/contract/test_cases_list_api.py`（GET /cases 各篩選組合、分頁、空結果）
- [ ] T042 [P] [US2] 寫 unit test：`backend/tests/unit/test_file_parser_service.py`（Excel 解析、CSV 解析、Tab-分隔解析、格式錯誤回傳具體訊息）
- [ ] T043 [P] [US2] 寫 integration test：`backend/tests/integration/test_case_filtering.py`（system_category 篩選、keyword 搜尋、多條件 AND）

### 實作

- [ ] T044 [US2] 在 `backend/src/repositories/test_case_repo.py` 加入 `list_with_filters(system_category, keyword, tags, page, page_size)`（使用 SQLAlchemy `ilike` + 分頁）
- [ ] T045 [US2] 在 `backend/src/api/cases.py` 加入 `GET /cases`（query params 篩選 + 分頁，回傳 items + total）
- [ ] T046 [P] [US2] 建立 `backend/src/services/file_parser_service.py`（FileParserService：parse_excel, parse_csv, parse_text, map_columns, generate_preview）
- [ ] T047 [US2] 在 `backend/src/api/cases.py` 加入 `POST /cases/{id}/import-test-data`（multipart 上傳 → 呼叫 FileParserService → 回傳預覽 + import_token）及 `.../confirm`（依 token 寫入 TestData）
- [ ] T048 [P] [US2] 建立 `frontend/src/components/TestCaseList/index.vue`（條列式清單 + 篩選欄：系統別下拉、關鍵字輸入、分頁）
- [ ] T049 [P] [US2] 建立 `frontend/src/pages/CasesPage.vue`（整合 TestCaseList + 篩選狀態管理，連接 caseApi）
- [ ] T050 [US2] 建立 `frontend/src/pages/CaseDetailPage.vue`（完整欄位顯示 + 版本歷史列表 + 執行歷史入口 + Excel/CSV 匯入按鈕）
- [ ] T051 [US2] 建立 `frontend/src/components/FileImporter/index.vue`（拖曳/點擊上傳 Excel/CSV/文字檔，顯示解析預覽並確認匯入）
- [ ] T052 [US2] 在 `backend/src/api/cases.py` 加入 `GET /cases/{id}/execution-history`（查詢該案例所屬的所有 ExecutionRecord 摘要）
- [ ] T053 [P] [US2] 建立 DB index：在 `alembic` migration 中為 `test_cases.system_category`、`test_cases.name`、`test_cases.is_deleted` 建立索引

**Checkpoint**: 清單頁篩選功能完整；詳情頁顯示所有欄位；Excel 上傳後預覽 10 筆並確認匯入

---

## Phase 5: User Story 3 — 測試清單管理（Priority: P2）

**Goal**: 測試人員可建立/編輯測試清單，加入/移除案例，查看每次執行的歷史紀錄並點入詳情

**Independent Test**: 建立清單後加入 3 個案例並儲存，清單頁顯示完整；可移除其中 1 個案例不影響其餘

### TDD 測試（先寫、確認 RED）

- [ ] T054 [P] [US3] 寫 contract test：`backend/tests/contract/test_checklists_api.py`（POST /checklists、GET /checklists/{id}、PUT /checklists/{id}/items、移除案例）
- [ ] T055 [P] [US3] 寫 integration test：`backend/tests/integration/test_checklist_with_history.py`（建立清單、建立 ExecutionRecord、查看歷史）

### 實作

- [ ] T056 [P] [US3] 建立 `backend/src/models/test_checklist.py`（TestChecklist ORM）及 `backend/src/models/checklist_item.py`（ChecklistItem ORM + unique constraint）
- [ ] T057 [P] [US3] 建立 `backend/src/models/execution_record.py`（ExecutionRecord ORM：完整欄位含 status ENUM、parallel_mode、max_workers、counts）
- [ ] T058 [US3] 執行 `alembic revision --autogenerate -m "add_checklist_tables"` 並驗證
- [ ] T059 [US3] 建立 `backend/src/repositories/checklist_repo.py`（ChecklistRepository：含 get_with_items、get_execution_history）
- [ ] T060 [US3] 建立 `backend/src/services/checklist_service.py`（ChecklistService：create, update_items, get_with_history, validate_cases_exist）
- [ ] T061 [US3] 建立 `backend/src/api/checklists.py`（POST /checklists、GET /checklists、GET /checklists/{id}、PUT /checklists/{id}/items）並掛載至 main.py
- [ ] T062 [P] [US3] 建立 `frontend/src/services/checklistApi.ts`（createChecklist, getChecklist, listChecklists, updateItems）
- [ ] T063 [P] [US3] 建立 `frontend/src/pages/ChecklistsPage.vue`（清單列表 + 建立清單入口）
- [ ] T064 [US3] 建立 `frontend/src/components/ChecklistView/index.vue`（顯示清單名稱、案例列表（可移除）、執行歷史表格，點擊進入詳情）
- [ ] T065 [US3] 建立 `frontend/src/pages/ChecklistDetailPage.vue`（整合 ChecklistView，連接 checklistApi）

**Checkpoint**: 可建立清單、加入/移除案例、查看執行歷史（目前為空，等 US5 後填充）

---

## Phase 6: User Story 4 — 串接資料庫撈取測試資料（Priority: P3）

**Goal**: 測試人員可設定外部 SQLite 資料庫連線、測試連線可用性、執行查詢並將結果套用至測試案例測試資料欄位

**Independent Test**: 設定 SQLite 連線並測試成功；查詢回傳資料列表；套用至測試案例欄位後可查看

### TDD 測試（先寫、確認 RED）

- [ ] T066 [P] [US4] 寫 contract test：`backend/tests/contract/test_db_connections_api.py`（POST /db-connections、POST /test、POST /query 成功 + 失敗）
- [ ] T067 [P] [US4] 寫 unit test：`backend/tests/unit/test_db_connect_service.py`（SQLite 連線測試、查詢執行、timeout 處理）

### 實作

- [ ] T068 [P] [US4] 建立 `backend/src/models/db_connection.py`（DBConnection ORM：含 EncryptedType for connection_string）
- [ ] T069 [US4] 執行 `alembic revision --autogenerate -m "add_db_connection"` 並驗證
- [ ] T070 [US4] 建立 `backend/src/services/db_connect_service.py`（DBConnectionService：test_connection, execute_query，隔離連線避免影響主 DB）
- [ ] T071 [US4] 建立 `backend/src/api/db_connections.py`（POST /db-connections、GET /db-connections、POST /{id}/test、POST /{id}/query）並掛載
- [ ] T072 [P] [US4] 建立 `frontend/src/pages/DBConnectionPage.vue`（連線設定表單 + 測試連線 + 查詢介面 + 選取套用至案例的流程）

**Checkpoint**: 設定 SQLite 連線測試成功；`SELECT * FROM table` 查詢結果出現在選取列表

---

## Phase 7: User Story 5 — 執行網頁測試與產生報告（Priority: P3）

**Goal**: 測試人員可對測試清單執行平行自動化測試，AI 自動翻譯步驟，透過 SSE 即時顯示進度；執行完成後在網頁查看含截圖/影片的結構化結果

**Independent Test**: 選取清單執行後 SSE 收到進度事件；執行完成後結果頁面顯示案例通過/失敗及截圖

### TDD 測試（先寫、確認 RED）

- [ ] T073 [P] [US5] 寫 contract test：`backend/tests/contract/test_executions_api.py`（POST /checklists/{id}/execute 202、GET /executions/{id}、GET /executions/{id}/results）
- [ ] T074 [P] [US5] 寫 unit test：`backend/tests/unit/test_execution_service.py`（Semaphore 平行控制、timeout 處理、trial run 與正式執行區隔）
- [ ] T075 [P] [US5] 寫 unit test：`backend/tests/unit/test_report_service.py`（XML 解析、status mapping、media 路徑提取）
- [ ] T076 [P] [US5] 寫 integration test：`backend/tests/integration/test_robot_execution.py`（Robot Framework subprocess 呼叫、output.xml 解析）
- [ ] T077 [P] [US5] 寫 unit test：`backend/tests/unit/test_ai_service_codegen.py`（generate_robot_code、快取命中不重複呼叫 LLM、模糊步驟標記 unable_to_generate）

### 實作（後端）

- [ ] T078 [P] [US5] 建立 `backend/src/models/automation_code.py`（AutomationCode ORM：完整欄位含 unique constraint (test_case_id, case_version)）
- [ ] T079 [P] [US5] 建立 `backend/src/models/case_result.py`（CaseResult ORM）及 `backend/src/models/execution_media.py`（ExecutionMedia ORM）
- [ ] T080 [US5] 執行 `alembic revision --autogenerate -m "add_execution_tables"` 並驗證
- [ ] T081 [US5] 完善 `backend/src/services/ai_service.py` 的 `generate_robot_code()`（呼叫 LLM 生成 .robot 代碼、快取檢查、模糊步驟標記、結果存入 AutomationCode）
- [ ] T082 [US5] 建立 `backend/src/services/execution_service.py`（ExecutionService：run_single_case（RF subprocess + timeout）、run_checklist_parallel（asyncio.Semaphore）、run_trial（trial_run 標記）、update_case_status）
- [ ] T083 [US5] 建立 `backend/src/services/report_service.py`（ReportService：parse_xml、extract_media_paths、build_case_results、persist_to_db）
- [ ] T084 [US5] 在 `backend/src/api/checklists.py` 加入 `POST /{id}/execute`（回傳 202 + execution_id + stream_url，背景啟動執行）
- [ ] T085 [US5] 建立 `backend/src/api/executions.py`（GET /executions/{id}、GET /executions/{id}/results、GET /executions/{id}/stream（SSE）、GET /media/results/...）並掛載
- [ ] T086 [US5] 在 `backend/src/api/cases.py` 完善 `POST /cases/{id}/trial-run`（呼叫 execution_service.run_trial，回傳 202 + stream_url）
- [ ] T087 [US5] 建立 `backend/src/api/media.py`（GET /media/attachments/{case_id}/{filename}、GET /media/results/{execution_id}/screenshots/{filename}、GET /media/results/{execution_id}/videos/{filename} with Range support）

### 實作（前端）

- [ ] T088 [P] [US5] 建立 `frontend/src/services/executionApi.ts`（executeChecklist, getExecution, getResults, streamExecution using EventSource）
- [ ] T089 [P] [US5] 建立 `frontend/src/stores/executionStore.ts`（Pinia：executionStatus, caseResults, handleSSEEvent）
- [ ] T090 [US5] 建立 `frontend/src/components/ExecutionProgress/index.vue`（SSE 訂閱、即時進度顯示：每個案例狀態條、整體進度條、平行執行視覺化）
- [ ] T091 [US5] 建立 `frontend/src/components/ResultViewer/index.vue`（案例結果卡片：status badge、elapsed time、失敗訊息、截圖縮圖列表（點擊放大）、影片串流播放）
- [ ] T092 [US5] 建立 `frontend/src/pages/ExecutionPage.vue`（整合 ExecutionProgress，執行完成後自動導向 ResultPage）
- [ ] T093 [US5] 建立 `frontend/src/pages/ResultPage.vue`（整合 ResultViewer，顯示所有案例結果，媒體按步驟順序排列）
- [ ] T094 [US5] 在 `frontend/src/components/ChecklistView/index.vue` 加入「執行測試」按鈕（含平行執行開關 + 並行數設定）

**Checkpoint**: 選取清單點擊執行，瀏覽器收到 SSE 進度事件；執行完成後結果頁顯示截圖

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 效能、強固性、文件最終化

- [ ] T095 [P] 建立 DB index migration：`test_cases(system_category)`, `test_cases(case_number)`, `case_results(execution_id)`, `execution_media(case_result_id)`（`backend/alembic/versions/xxx_add_indexes.py`）
- [ ] T096 [P] 在 `backend/src/core/dependencies.py` 加入統一 LLM API error handler（503 service unavailable + retry hint）及 media file not found handler（占位圖片回傳）
- [ ] T097 建立 `backend/src/api/llm_models.py`（`GET /llm-models` 回傳可用模型列表）並掛載
- [ ] T098 [P] 建立 `frontend/src/components/LLMModelSelector/index.vue`（模型選擇下拉，呼叫 `/llm-models` 動態載入）並整合至 TestCaseForm
- [ ] T099 [P] 補充 `backend/tests/unit/` 中各 service 的邊界條件測試（空案例清單執行、AI timeout、媒體損毀）
- [ ] T100 依 `specs/001-auto-test-platform/quickstart.md` 執行完整功能驗證：建立案例→AI 補齊→建清單→執行→查看結果

---

## Dependencies & Execution Order

### Phase 依賴

- **Phase 1（Setup）**: 無依賴，立即開始
- **Phase 2（Foundational）**: 依賴 Phase 1 完成 — **阻塞所有 User Story**
- **Phase 3（US1, P1）**: 依賴 Phase 2 — 無其他 User Story 依賴
- **Phase 4（US2, P1）**: 依賴 Phase 2 — 需要 Phase 3 的 TestCase model（T024）
- **Phase 5（US3, P2）**: 依賴 Phase 2 — 需要 Phase 3 的 CaseService（T029）
- **Phase 6（US4, P3）**: 依賴 Phase 2 — 可與 Phase 3/4/5 平行
- **Phase 7（US5, P3）**: 依賴 Phase 3（AutomationCode model）+ Phase 5（ExecutionRecord model）
- **Phase 8（Polish）**: 依賴所有想要交付的 User Story 完成

### User Story 間依賴摘要

| Story | 依賴 | 說明 |
|-------|------|------|
| US1 | Phase 2 | 獨立 MVP |
| US2 | Phase 2 + T024（TestCase model） | TestCase model 共用 |
| US3 | Phase 2 + T029（CaseService）| 需驗證案例存在 |
| US4 | Phase 2 | 獨立 |
| US5 | T024（TestCase）+ T057（ExecutionRecord）| 需代碼生成 + 執行紀錄 |

### Story 內依賴順序（US1 範例）

```
T019–T023（測試，RED）
    ↓ 平行執行
T024–T026（Models）→ T027（Migration）→ T028（Repository）→ T029（Service）→ T033（API）
    ↓ 平行執行
T034–T037（Frontend Components）→ T038（Page）
    ↓
T039（Trial Run 按鈕）
    ↓
T040（Frontend Test）
```

---

## Parallel Opportunities

### Phase 1（全部可平行）
```
T001 ‖ T002 ‖ T003 ‖ T004 ‖ T005 ‖ T006 ‖ T007 ‖ T008
```

### Phase 3（US1）- 測試與 Model 可平行
```
T019 ‖ T020 ‖ T021 ‖ T022 ‖ T023     （測試先 RED）
T024 ‖ T025 ‖ T026                    （Models 平行）
T031 ‖ T034 ‖ T035 ‖ T036 ‖ T037     （LLM provider + Frontend 平行）
```

### Phase 7（US5）- 後端與前端可平行
```
T073 ‖ T074 ‖ T075 ‖ T076 ‖ T077     （測試先 RED）
T078 ‖ T079                            （Models 平行）
T088 ‖ T089                            （Frontend services + stores 平行）
T090 ‖ T091                            （Frontend components 平行）
```

---

## Implementation Strategy

### MVP（僅 User Story 1）

1. 完成 Phase 1：Setup
2. 完成 Phase 2：Foundational（**CRITICAL**）
3. 完成 Phase 3：User Story 1
4. **STOP & VALIDATE**：用 curl 建立案例、AI 補齊、媒體上傳、試跑
5. Demo / 部署 MVP

### Incremental Delivery

1. Setup + Foundational → 基礎就緒
2. US1（建立案例）→ MVP，可 demo
3. US2（瀏覽篩選）→ 清單管理完整
4. US3（測試清單）→ 清單工作流完整
5. US5（執行與報告）→ 核心自動化完整（跳過 US4）
6. US4（DB 串接）→ 進階測資管理

### Parallel Team Strategy

```
Phase 2 完成後：
  Developer A：US1（建立測試案例）
  Developer B：US2（瀏覽篩選）  ← 需等 Developer A 完成 T024
  Developer C：US4（DB 串接）   ← 完全獨立
```

---

## Notes

- `[P]` = 不同檔案，無未完成依賴，可平行執行
- `[Story]` 標籤對應 spec.md 中的 User Story
- TDD 順序嚴格：先寫測試確認 RED，再實作直到 GREEN，再 Refactor
- 每個測試任務必須在對應實作任務開始前存在且失敗
- 每完成一個 Phase 的 Checkpoint 後 commit
- 避免：模糊描述、相同檔案衝突、跨 Story 的破壞性依賴
