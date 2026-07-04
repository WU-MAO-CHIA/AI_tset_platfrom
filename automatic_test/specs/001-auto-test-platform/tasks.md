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

- [X] T001 建立 backend 目錄結構：`backend/src/{models,repositories,services,api,core,templates}/`、`backend/tests/{unit,integration,contract}/`
- [X] T002 [P] 建立 frontend 目錄結構：`frontend/src/{components,pages,services,stores,types}/`、`frontend/tests/{unit,e2e}/`
- [X] T003 [P] 建立 `robot_scripts/{generated,results}/` 目錄結構及 `.gitkeep`
- [X] T004 建立 `backend/requirements.txt`（fastapi, uvicorn, sqlalchemy, alembic, python-multipart, aiofiles, httpx, openpyxl, robotframework, robotframework-browser, anthropic, openai, validators, sqlalchemy-utils, jinja2）及 `backend/requirements-dev.txt`（pytest, pytest-asyncio, pytest-cov, httpx）
- [X] T005 [P] 建立 `frontend/package.json`（vue 3, typescript, pinia, vue-router 4, axios, vueuse）及 `frontend/vite.config.ts`
- [X] T006 建立 `backend/.env.example`（DATABASE_URL, MEDIA_ROOT, ROBOT_SCRIPTS_DIR, PARALLEL_MAX_WORKERS, ANTHROPIC_API_KEY, OPENAI_API_KEY, DEFAULT_LLM_MODEL）
- [X] T007 [P] 建立 `backend/pytest.ini`（asyncio_mode=auto, testpaths=tests）及 `frontend/vitest.config.ts`
- [X] T008 建立 `backend/alembic.ini` 及執行 `alembic init backend/alembic/`（首次建立時執行，已存在時跳過）
- [X] T009 執行 `rfbrowser init` 安裝 Playwright 瀏覽器二進位檔（Chromium）至後端伺服器；確認 headless 模式可正常啟動（⚠️ 需手動執行：先 `pip install -r requirements.txt`，再 `rfbrowser init`）

**Checkpoint**: `pip install -r requirements.txt`、`npm install`、`rfbrowser init` 均無錯誤

---

## Phase 2: Foundational（阻塞性前置基礎）

**Purpose**: 所有 User Story 依賴的核心基礎架構

**⚠️ CRITICAL**: 此 Phase 完成前，任何 User Story 均不可開始

- [X] T010 建立 `backend/src/core/config.py`（pydantic-settings 讀取 .env，暴露 Settings singleton）
- [X] T011 建立 `backend/src/core/database.py`（SQLAlchemy async engine + AsyncSessionLocal + get_db dependency）
- [X] T012 [P] 建立 `backend/src/core/dependencies.py`（FastAPI dependency injection 工廠函式）
- [X] T013 建立 `backend/src/models/base.py`（SQLAlchemy DeclarativeBase + TimestampMixin with created_at/updated_at）
- [X] T014 建立 `backend/src/repositories/base.py`（Generic Repository ABC：get, list, create, update, delete）
- [X] T015 [P] 建立 `backend/src/main.py`（FastAPI app 初始化、CORS、exception handlers、router 掛載）
- [X] T016 建立 `backend/alembic/env.py`（設定 async migrations，import 所有 model）
- [X] T017 建立 `frontend/src/main.ts`（Vue app 初始化、Pinia、Vue Router）
- [X] T018 [P] 建立 `frontend/src/router/index.ts`（Vue Router 設定，預留所有頁面路由）
- [X] T019 建立 `frontend/src/services/apiClient.ts`（Axios instance，統一 baseURL、interceptor、error handling）
- [X] T020 更新 `specs/001-auto-test-platform/contracts/api.md`：在 Cases 段落補充 `GET /cases/{case_id}/execution-history` 端點規格（response 為 ExecutionRecord 摘要列表，含 execution_id、status、started_at、passed_count、failed_count）

**Checkpoint**: `uvicorn src.main:app` 啟動無錯誤；`npm run dev` 可存取 localhost:5173

---

## Phase 3: User Story 1 — 建立測試案例（Priority: P1）🎯 MVP

**Goal**: 測試人員可建立、編輯、刪除測試案例，含版本管理、AI 步驟補齊（含多媒體上下文）、多媒體附件上傳、立即試跑

**Independent Test**: `POST /api/v1/cases` 建立案例後出現於清單，版本號為 v1；AI 補齊回傳補充後的步驟；刪除後案例不再出現

### TDD 測試（先寫、確認 RED）

- [X] T021 [P] [US1] 寫 contract test：`backend/tests/contract/test_cases_api.py`（POST /cases 201、case_number 重複 409、PUT 版本遞增、DELETE 軟刪除 200、DELETE 被引用時回傳 `affected_checklists` 陣列含清單名稱）
- [X] T022 [P] [US1] 寫 unit test：`backend/tests/unit/test_case_service.py`（create、update 版本遞增、soft_delete、delete_blocked_returns_checklist_names）
- [X] T023 [P] [US1] 寫 integration test：`backend/tests/integration/test_case_crud.py`（完整 CRUD with real SQLite）
- [X] T024 [P] [US1] 寫 unit test：`backend/tests/unit/test_ai_service.py`（LLMProvider mock、complete_steps with/without media、provider 切換）
- [X] T025 [P] [US1] 寫 unit test：`backend/tests/unit/test_media_service.py`（上傳驗證、大小限制、路徑生成）
- [X] T026 [P] [US1] 寫 frontend unit test：`frontend/tests/unit/TestCaseForm.spec.ts`（必填驗證、AI 補齊觸發、媒體上傳互動、試跑按鈕顯示）

### 實作

- [X] T027 [P] [US1] 建立 `backend/src/models/test_case.py`（TestCase ORM：id, case_number UNIQUE, name, description, precondition_steps, main_steps NOT NULL, system_category, tags JSON, version default=1, created_by, modified_by, is_deleted, timestamps）
- [X] T028 [P] [US1] 建立 `backend/src/models/test_data.py`（TestData ORM：id, test_case_id FK, field_name, field_value, source ENUM, import_source_id, row_index）
- [X] T029 [P] [US1] 建立 `backend/src/models/media_attachment.py`（MediaAttachment ORM：id, test_case_id FK, attachment_type ENUM image/video/url, filename, file_path, url, file_size_bytes, mime_type）
- [X] T030 [US1] 執行 `alembic revision --autogenerate -m "add_test_case_tables"` 並驗證 migration upgrade/downgrade 正常
- [X] T031 [US1] 建立 `backend/src/repositories/test_case_repo.py`（TestCaseRepository：soft_delete, list_with_filters, get_by_case_number, increment_version, get_referencing_checklists_with_names）
- [X] T032 [US1] 建立 `backend/src/services/case_service.py`（CaseService：create, update 含版本遞增, soft_delete 含引用檢查——刪除被清單引用時回傳清單名稱列表而非 execution IDs）
- [X] T033 [US1] 建立 `backend/src/services/media_service.py`（MediaService：upload_attachment, validate_file_type_and_size, serve_file, delete_attachment）
- [X] T034 [P] [US1] 建立 `backend/src/core/llm_provider.py`（LLMProvider Protocol + AnthropicProvider + OpenAIProvider；`complete(prompt)` 及 `complete_with_vision(prompt, media_list)` 兩個介面）
- [X] T035 [US1] 建立 `backend/src/services/ai_service.py`（AIService：`complete_steps(steps, description, media_attachments=[])` 呼叫 LLM 時傳入 MediaAttachment 作為 vision 上下文；`generate_robot_code()` 骨架，注入 LLMProvider）
- [X] T036 [US1] 建立 `backend/src/api/cases.py`（FastAPI router：POST /cases、GET /cases/{id}、PUT /cases/{id}、DELETE /cases/{id}（錯誤回應含 `affected_checklists: [{id, name}]`）、POST /cases/{id}/ai-complete、POST /cases/{id}/attachments、POST /cases/{id}/trial-run）
- [X] T037 [US1] 建立 `frontend/src/services/caseApi.ts`（createCase, getCase, updateCase, deleteCase, aiComplete, uploadAttachment, trialRun）
- [X] T038 [US1] 建立 `frontend/src/stores/caseStore.ts`（Pinia store：currentCase, savingState, aiCompletionState）
- [X] T039 [P] [US1] 建立 `frontend/src/components/MediaUploader/index.vue`（圖片/影片上傳 + 網址輸入，含大小限制提示）
- [X] T040 [P] [US1] 建立 `frontend/src/components/TestCaseForm/index.vue`（表單：所有欄位輸入、TestData 動態新增、LLM 模型選擇、AI 補齊按鈕、媒體上傳區、「立即試跑」按鈕）
- [X] T041 [US1] 建立 `frontend/src/pages/CaseCreatePage.vue`（組合 TestCaseForm，連接 caseStore，處理儲存/AI 補齊/試跑觸發）

**Checkpoint**: 可用 `curl` 建立測試案例、AI 補齊成功回傳（含媒體上下文）、媒體上傳至本地路徑、刪除被引用案例顯示清單名稱

---

## Phase 4: User Story 2 — 瀏覽與篩選測試案例（Priority: P1）

**Goal**: 測試人員可多條件篩選案例清單、查看詳情（含版本歷史）、上傳 Excel/CSV 匯入測試參數、從案例查看執行歷史

**Independent Test**: 多條件篩選千筆案例 ≤2s；Excel 上傳後預覽正確；從案例詳情頁可看到執行歷史入口

### TDD 測試（先寫、確認 RED）

- [X] T042 [P] [US2] 寫 contract test：`backend/tests/contract/test_cases_list_api.py`（GET /cases 各篩選組合、分頁、空結果；GET /cases/{id}/execution-history 回傳正確結構）
- [X] T043 [P] [US2] 寫 unit test：`backend/tests/unit/test_file_parser_service.py`（Excel 解析、CSV 解析、Tab 分隔解析、格式錯誤回傳具體欄位說明）
- [X] T044 [P] [US2] 寫 integration test：`backend/tests/integration/test_case_filtering.py`（system_category 篩選、keyword 搜尋、多條件 AND、分頁正確）

### 實作

- [X] T045 [US2] 在 `backend/src/repositories/test_case_repo.py` 加入 `list_with_filters(system_category, keyword, tags, page, page_size)`（SQLAlchemy `ilike` + 分頁）
- [X] T046 [US2] 在 `backend/src/api/cases.py` 加入 `GET /cases`（query params 篩選 + 分頁，回傳 items + total）及 `GET /cases/{id}/execution-history`（查詢該案例所屬 ExecutionRecord 摘要）
- [X] T047 [P] [US2] 建立 `backend/src/services/file_parser_service.py`（FileParserService：parse_excel, parse_csv, parse_text, map_columns by header name, generate_preview）
- [X] T048 [US2] 在 `backend/src/api/cases.py` 加入 `POST /cases/{id}/import-test-data`（multipart → FileParserService → 預覽 + import_token）及 `.../confirm`（依 token 寫入 TestData）
- [X] T049 [P] [US2] 建立 `frontend/src/components/TestCaseList/index.vue`（條列式清單 + 篩選欄：系統別下拉、關鍵字輸入、分頁）
- [X] T050 [P] [US2] 建立 `frontend/src/pages/CasesPage.vue`（整合 TestCaseList + 篩選狀態管理，連接 caseApi）
- [X] T051 [US2] 建立 `frontend/src/pages/CaseDetailPage.vue`（完整欄位顯示 + 版本歷史列表 + 執行歷史入口 + Excel/CSV 匯入按鈕）
- [X] T052 [US2] 建立 `frontend/src/components/FileImporter/index.vue`（拖曳/點擊上傳 Excel/CSV/文字檔，顯示解析預覽並確認匯入）
- [X] T053 [P] [US2] 建立 DB index migration：`test_cases(system_category)`、`test_cases(name)`、`test_cases(is_deleted)`（`backend/alembic/versions/xxx_add_case_indexes.py`）

**Checkpoint**: 清單頁篩選功能完整；詳情頁顯示所有欄位；Excel 上傳後預覽 10 筆並確認匯入

---

## Phase 5: User Story 3 — 測試清單管理（Priority: P2）

**Goal**: 測試人員可建立/編輯測試清單，加入/移除案例，查看每次執行的歷史紀錄並點入詳情

**Independent Test**: 建立清單後加入 3 個案例並儲存，清單頁顯示完整；可移除其中 1 個案例不影響其餘

### TDD 測試（先寫、確認 RED）

- [X] T054 [P] [US3] 寫 contract test：`backend/tests/contract/test_checklists_api.py`（POST /checklists、GET /checklists/{id}、PUT /checklists/{id}/items、移除案例）
- [X] T055 [P] [US3] 寫 integration test：`backend/tests/integration/test_checklist_with_history.py`（建立清單、建立 ExecutionRecord、查看歷史）

### 實作

- [X] T056 [P] [US3] 建立 `backend/src/models/test_checklist.py`（TestChecklist ORM）及 `backend/src/models/checklist_item.py`（ChecklistItem ORM + unique constraint）
- [X] T057 [P] [US3] 建立 `backend/src/models/execution_record.py`（ExecutionRecord ORM：`checklist_id` nullable FK(TestChecklist.id)、`source_case_id` nullable FK(TestCase.id)、execution_type ENUM、status ENUM、parallel_mode、max_workers、counts、timestamps；CHECK constraint：checklist_id 與 source_case_id 恰好一個有值）
- [X] T058 [US3] 執行 `alembic revision --autogenerate -m "add_checklist_tables"` 並驗證
- [X] T059 [US3] 建立 `backend/src/repositories/checklist_repo.py`（ChecklistRepository：get_with_items、get_execution_history）
- [X] T060 [US3] 建立 `backend/src/repositories/execution_repo.py`（ExecutionRepository：create_for_checklist、create_for_trial_run（填入 source_case_id）、update_status、get_case_results_summary）
- [X] T061 [US3] 建立 `backend/src/services/checklist_service.py`（ChecklistService：create, update_items, get_with_history, validate_cases_exist）
- [X] T062 [US3] 建立 `backend/src/api/checklists.py`（POST /checklists、GET /checklists、GET /checklists/{id}、PUT /checklists/{id}/items）並掛載至 main.py
- [X] T063 [P] [US3] 建立 `frontend/src/services/checklistApi.ts`（createChecklist, getChecklist, listChecklists, updateItems）
- [X] T064 [P] [US3] 建立 `frontend/src/pages/ChecklistsPage.vue`（清單列表 + 建立清單入口）
- [X] T065 [US3] 建立 `frontend/src/components/ChecklistView/index.vue`（顯示清單名稱、案例列表（可移除）、執行歷史表格，點擊進入詳情）
- [X] T066 [US3] 建立 `frontend/src/pages/ChecklistDetailPage.vue`（整合 ChecklistView，連接 checklistApi）

**Checkpoint**: 可建立清單、加入/移除案例、查看執行歷史（目前為空，等 US5 後填充）

---

## Phase 6: User Story 4 — 串接資料庫撈取測試資料（Priority: P3）

**Goal**: 測試人員可設定外部 SQLite 資料庫連線、測試連線可用性、執行查詢並將結果套用至測試案例測試資料欄位

**Independent Test**: 設定 SQLite 連線並測試成功；查詢回傳資料列表；套用至測試案例欄位後可查看

### TDD 測試（先寫、確認 RED）

- [X] T067 [P] [US4] 寫 contract test：`backend/tests/contract/test_db_connections_api.py`（POST /db-connections、POST /test 成功+失敗、POST /query 成功+timeout）
- [X] T068 [P] [US4] 寫 unit test：`backend/tests/unit/test_db_connect_service.py`（SQLite 連線測試、查詢執行、timeout 處理、隔離連線不影響主 DB）

### 實作

- [X] T069 [P] [US4] 建立 `backend/src/models/db_connection.py`（DBConnection ORM：含 EncryptedType for connection_string、last_tested_at、last_test_success）
- [X] T070 [US4] 執行 `alembic revision --autogenerate -m "add_db_connection"` 並驗證
- [X] T071 [US4] 建立 `backend/src/services/db_connect_service.py`（DBConnectionService：test_connection, execute_query，使用獨立連線池，避免影響主 DB）
- [X] T072 [US4] 建立 `backend/src/api/db_connections.py`（POST /db-connections、GET /db-connections、POST /{id}/test、POST /{id}/query）並掛載
- [X] T073 [P] [US4] 建立 `frontend/src/pages/DBConnectionPage.vue`（連線設定表單 + 測試連線 + 查詢介面 + 選取套用至案例的流程）

**Checkpoint**: 設定 SQLite 連線測試成功；`SELECT * FROM table` 查詢結果出現在選取列表

---

## Phase 7: User Story 5 — 執行網頁測試與產生報告（Priority: P3）

**Goal**: 測試人員可對測試清單執行平行自動化測試，AI 自動翻譯步驟，透過 SSE 即時顯示進度；執行完成後在網頁查看含截圖/影片的結構化結果，並可下載 HTML 報告

**Independent Test**: 選取清單執行後 SSE 收到進度事件；執行完成後結果頁顯示案例通過/失敗及截圖；「匯出報告」觸發 HTML 下載

### TDD 測試（先寫、確認 RED）

- [X] T074 [P] [US5] 寫 contract test：`backend/tests/contract/test_executions_api.py`（POST /checklists/{id}/execute 202、GET /executions/{id}、GET /executions/{id}/results、GET /executions/{id}/export 200 Content-Disposition）
- [X] T075 [P] [US5] 寫 unit test：`backend/tests/unit/test_execution_service.py`（RF subprocess 每案例執行驗證、.robot 檔讀取路徑、timeout 處理、trial run 填入 source_case_id、checklist 執行填入 checklist_id；⚠️ pabot 驗證改由 T168 實作後更新此測試）
- [X] T076 [P] [US5] 寫 unit test：`backend/tests/unit/test_report_service.py`（XML 解析、status mapping、media 路徑提取、export_report 回傳有效 HTML）
- [X] T077 [P] [US5] 寫 integration test：`backend/tests/integration/test_robot_execution.py`（Robot Framework subprocess 呼叫、output.xml 解析、截圖路徑存入 DB）
- [X] T078 [P] [US5] 寫 unit test：`backend/tests/unit/test_ai_service_codegen.py`（generate_robot_code、快取命中不重複呼叫 LLM、模糊步驟標記 unable_to_generate、35s timeout 後標記失敗繼續執行）

### 實作（後端）

- [X] T079 [P] [US5] 建立 `backend/src/models/automation_code.py`（AutomationCode ORM：test_case_id FK, case_version, code_content, llm_model, generation_status ENUM, error_message；UNIQUE(test_case_id, case_version)）
- [X] T080 [P] [US5] 建立 `backend/src/models/case_result.py`（CaseResult ORM：execution_id FK, test_case_id FK, case_version, automation_code_id FK nullable, status ENUM, elapsed_ms, failure_message, position）及 `backend/src/models/execution_media.py`（ExecutionMedia ORM：case_result_id FK, media_type ENUM, file_path, step_index, step_name）
- [X] T081 [US5] 執行 `alembic revision --autogenerate -m "add_execution_tables"` 並驗證
- [X] T082 [US5] 完善 `backend/src/services/ai_service.py` 的 `generate_robot_code()`（快取檢查 AutomationCode、呼叫 LLM 生成 .robot 代碼、模糊步驟標記 unable_to_generate、設定 35s timeout 後標記 failed 並繼續、存入 AutomationCode）
- [X] T083 [US5] 建立 `backend/src/services/execution_service.py`（ExecutionService 骨架：`run_checklist`（目前使用 per-case asyncio.create_task + RF subprocess 讀 .robot 檔，checklist_id 填入 ExecutionRecord）、`run_trial`（source_case_id 填入 ExecutionRecord，execution_type=trial_run，不計入清單歷史）；⚠️ pabot 整合為 Phase 17 T168，尚未完成）
- [X] T084 [US5] 建立 `backend/src/services/report_service.py`（ReportService：parse_xml, extract_media_paths, build_case_results, persist_to_db；`export_report(execution_id)` 使用 Jinja2 渲染 `report.html.j2` 回傳 HTML 字串）
- [X] T085 [US5] 建立 `backend/src/templates/report.html.j2`（HTML 報告 Jinja2 template：標題含執行時間/通過率、案例結果列表（status badge、elapsed_ms、failure_message）、截圖縮圖列表）
- [X] T086 [US5] 在 `backend/src/api/checklists.py` 加入 `POST /{id}/execute`（回傳 202 + execution_id + stream_url，背景啟動 execution_service.run_checklist_parallel）
- [X] T087 [US5] 建立 `backend/src/api/executions.py`（GET /executions/{id}、GET /executions/{id}/results、GET /executions/{id}/stream（SSE，依 contracts/sse.md 事件格式）、GET /executions/{id}/export（Content-Disposition attachment HTML）、GET /media/results/...）並掛載
- [X] T088 [US5] 在 `backend/src/api/cases.py` 完善 `POST /cases/{id}/trial-run`（呼叫 execution_service.run_trial，回傳 202 + stream_url）
- [X] T089 [US5] 建立 `backend/src/api/media.py`（GET /media/attachments/{case_id}/{filename}、GET /media/results/{execution_id}/screenshots/{filename}、GET /media/results/{execution_id}/videos/{filename} with HTTP Range support）

### 實作（前端）

- [X] T090 [P] [US5] 建立 `frontend/src/services/executionApi.ts`（executeChecklist, getExecution, getResults, streamExecution using EventSource, exportReport 觸發瀏覽器下載）
- [X] T091 [P] [US5] 建立 `frontend/src/stores/executionStore.ts`（Pinia：executionStatus, caseResults, handleSSEEvent 依 sse.md 事件格式）
- [X] T092 [US5] 建立 `frontend/src/components/ExecutionProgress/index.vue`（SSE 訂閱、即時進度顯示：每個案例狀態條、整體進度條、平行執行視覺化）
- [X] T093 [US5] 建立 `frontend/src/components/ResultViewer/index.vue`（案例結果卡片：status badge、elapsed time、失敗訊息、截圖縮圖列表（點擊放大）、影片串流播放）
- [X] T094 [US5] 建立 `frontend/src/pages/ExecutionPage.vue`（整合 ExecutionProgress，執行完成後自動導向 ResultPage）
- [X] T095 [US5] 建立 `frontend/src/pages/ResultPage.vue`（整合 ResultViewer，顯示所有案例結果，媒體按步驟順序排列；加入「匯出報告」按鈕呼叫 exportReport，觸發 HTML 檔案下載，對應 FR-011）
- [X] T096 [US5] 在 `frontend/src/components/ChecklistView/index.vue` 加入「執行測試」按鈕（含平行執行開關 + max_workers 設定）

**Checkpoint**: 選取清單點擊執行，瀏覽器收到 SSE 進度事件；執行完成後結果頁顯示截圖；「匯出報告」下載 HTML 檔案

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 效能、強固性、文件最終化

- [X] T097 [P] 建立 DB index migration：`test_cases(case_number)`、`case_results(execution_id)`、`execution_media(case_result_id)`（`backend/alembic/versions/xxx_add_perf_indexes.py`）
- [X] T098 [P] 在 `backend/src/core/dependencies.py` 加入統一 LLM API error handler（503 + retry hint）及 media file not found handler（占位圖片回傳）
- [X] T099 建立 `backend/src/api/llm_models.py`（`GET /llm-models` 回傳可用模型列表，從 Settings 讀取 API key 設定判斷可用性）並掛載
- [X] T100 [P] 建立 `frontend/src/components/LLMModelSelector/index.vue`（模型選擇下拉，呼叫 `/llm-models` 動態載入）並整合至 TestCaseForm
- [X] T101 [P] 補充 `backend/tests/unit/` 邊界條件測試（空案例清單執行、AI timeout 35s 後標記 failed 繼續、媒體損毀占位回傳、trial run source_case_id 正確填入而非 checklist_id）
- [X] T102 依 `specs/001-auto-test-platform/quickstart.md` 執行完整功能驗證：建立案例 → AI 補齊（含媒體上下文）→ 建清單 → 執行 → 查看結果 → 匯出報告

---

## Dependencies & Execution Order

### Phase 依賴

- **Phase 1（Setup）**: 無依賴，立即開始
- **Phase 2（Foundational）**: 依賴 Phase 1 完成 — **阻塞所有 User Story**
- **Phase 3（US1, P1）**: 依賴 Phase 2 — 無其他 User Story 依賴
- **Phase 4（US2, P1）**: 依賴 Phase 2 — 需要 Phase 3 的 TestCase model（T027）
- **Phase 5（US3, P2）**: 依賴 Phase 2 — 需要 Phase 3 的 CaseService（T032）
- **Phase 6（US4, P3）**: 依賴 Phase 2 — 可與 Phase 3/4/5 完全平行
- **Phase 7（US5, P3）**: 依賴 Phase 3（T027 TestCase model）+ Phase 5（T057 ExecutionRecord model）
- **Phase 8（Polish）**: 依賴所有想要交付的 User Story 完成

### User Story 間依賴摘要

| Story | 依賴 | 說明 |
|-------|------|------|
| US1 | Phase 2 | 獨立 MVP |
| US2 | Phase 2 + T027（TestCase model） | TestCase model 共用 |
| US3 | Phase 2 + T032（CaseService） | 需驗證案例存在 |
| US4 | Phase 2 | 獨立 |
| US5 | T027（TestCase）+ T057（ExecutionRecord，含 nullable FK 設計） | 需代碼生成 + 執行紀錄 |

### Story 內依賴順序（US1 範例）

```
T021–T026（測試，RED）
    ↓ 平行執行
T027–T029（Models）→ T030（Migration）→ T031（Repository）→ T032（Service）→ T036（API）
    ↓ 平行執行
T034（LLM Provider）‖ T037（caseApi）‖ T038（store）‖ T039（MediaUploader）
    ↓
T040（TestCaseForm）→ T041（Page）
```

---

## Parallel Opportunities

### Phase 1（大多可平行）
```
T001 ‖ T002 ‖ T003 ‖ T004 ‖ T005 ‖ T006 ‖ T007
T008 → T009（alembic init 後執行 rfbrowser init）
```

### Phase 3（US1）- 測試與 Model 可平行
```
T021 ‖ T022 ‖ T023 ‖ T024 ‖ T025 ‖ T026   （測試先 RED）
T027 ‖ T028 ‖ T029                           （Models 平行）
T034 ‖ T037 ‖ T038 ‖ T039                   （LLM provider + Frontend 平行）
```

### Phase 7（US5）- 後端與前端可平行
```
T074 ‖ T075 ‖ T076 ‖ T077 ‖ T078   （測試先 RED）
T079 ‖ T080                          （Models 平行）
T090 ‖ T091                          （Frontend services + stores 平行）
T092 ‖ T093                          （Frontend components 平行）
```

---

## Implementation Strategy

### MVP（僅 User Story 1）

1. 完成 Phase 1：Setup（含 T009 rfbrowser init）
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
  Developer B：US2（瀏覽篩選）  ← 需等 Developer A 完成 T027
  Developer C：US4（DB 串接）   ← 完全獨立
```

---

## Phase 9: Enhancements（後續優化，2026-05-20）

**Purpose**: AI 補齊按鈕修復、全域導覽列、字體更新、測試補齊、啟動文件

### AI 補齊按鈕修復（FR-US1）

- [X] T103 [US1] 新增 `POST /api/v1/cases/ai-complete`（stateless，無需 case_id）端點在 `backend/src/api/cases.py`；確保路由在 `/{case_id}` 之前宣告以避免路徑衝突
- [X] T104 [P] [US1] 在 `frontend/src/services/caseApi.ts` 新增 `aiCompletePreview()` 方法呼叫新端點
- [X] T105 [US1] 更新 `frontend/src/components/TestCaseForm/index.vue` 的 `onAiComplete()`：移除 `!props.caseId` early-return，改為依 `caseId` 有無選擇 `aiComplete()` 或 `aiCompletePreview()`

### 全域導覽列（FR-022）

- [X] T106 重寫 `frontend/src/App.vue`：加入 sticky 全域導覽列（含「測試案例管理」、「測試清單」、「資料庫連線」快速連結），以 `active-class` 高亮目前頁面

### 字體更新

- [X] T107 [P] 更新 `frontend/index.html`：加入 Noto Sans TC Google Fonts preconnect + stylesheet（wght 400/500/600/700）
- [X] T108 [P] 更新 `frontend/src/App.vue` 全域 CSS：`font-family` 改為 `'Noto Sans TC', system-ui, -apple-system, sans-serif`

### 前端測試補齊

- [X] T109 重寫 `frontend/tests/unit/TestCaseForm.spec.ts`：將 8 個 placeholder RED stub 替換為實際測試（mount + vi.mock caseApi + stubs for MediaUploader/LLMModelSelector），修正 `find('textarea')` 精確定位為 `find('textarea[required]')`

### 維護

- [X] T110 [P] 升級 `backend/requirements.txt` 中 `robotframework-browser==18.6.0` → `>=18.9.0` 以支援 Python 3.13 wheel（解決 grpcio-tools 編譯錯誤）
- [X] T111 [P] 建立 `automatic_test/STARTUP.md`（後端 / 前端啟動步驟、資料庫管理、測試執行、目錄結構、常見問題）

**Checkpoint**: `npm run test` 8/8 PASS；後端 100/100 PASS；`npm run dev` 可看到導覽列與 Noto Sans TC 字體

---

## Phase 10: Post-Analysis Remediation（分析後修正，2026-05-21）

**Purpose**: 修正 `/speckit-analyze` 找出的 6 項文件不一致，補充 SC-006/SC-009 缺少的測試覆蓋

### 規格文件修正

- [X] T112 [P] 修正 `automatic_test/.specify/memory/constitution.md` 第 51 行：`Use Python 3.14` → `Use Python 3.11+`（CRITICAL：3.14 尚未發布，constitution 應與 plan.md Python 3.11+ 一致）
- [X] T113 [P] 修正 `specs/001-auto-test-platform/spec.md` SC-010：`30 秒` → `35 秒`（HIGH：T082 實作設定 35s timeout，SC-010 說 30 秒形成矛盾）
- [X] T114 [P] 更新 `specs/001-auto-test-platform/spec.md` FR-006b：將 FR-006b 文字（清單執行歷史顯示）合併至 FR-006 末段，刪除 FR-006b 條目（HIGH：FR-006 與 FR-006b 指向同一需求，應合為一條）
- [X] T115 [P] 更新 `specs/001-auto-test-platform/spec.md` Clarifications 段落：移除 FR-022 重複引用塊（`> **FR-022（補充）**...`），保留 `### Session 2026-05-20` 下的 Q&A 說明即可（MEDIUM：FR-022 已在 Functional Requirements 正式定義，引用塊重複且易造成混淆）

### 測試覆蓋補充（SC-006 / SC-009）

- [X] T116 [P] [US5] 建立 `backend/tests/load/test_concurrent_users.py`：使用 `asyncio.gather` 模擬 10 個並發使用者同時呼叫 `GET /cases`，斷言 p95 回應時間 ≤ 2000ms（對應 SC-006 & SC-002：10 位測試人員同時操作不出現效能衰退）
- [X] T117 [P] [US5] 建立 `backend/tests/load/test_parallel_benchmark.py`：建立含 10 個案例的執行紀錄，比較平行執行（max_workers=5）vs 循序執行的模擬耗時，斷言平行時間 ≤ 循序時間 × 0.6（即縮短 ≥ 40%，對應 SC-009）

**Checkpoint**: T112–T115 文件已更新；`pytest backend/tests/load/` 兩個測試通過

---

## Phase 11: UI Layout Refactor — 左右分割版面（FR-001，2026-05-22）

**Purpose**: 依 PRD.md 更新後的 FR-001，將「建立測試案例」畫面重構為左右兩欄版面（僅 CaseCreatePage，編輯頁維持單欄）：右欄專注步驟撰寫與 AI 溝通（含 RF 程式碼預覽），左欄放置其餘欄位

> **TDD 順序**：測試先寫（RED）→ 後端端點 → 前端元件實作（GREEN）

### 步驟一：先寫測試（RED 階段）

- [X] T118 [P] [US1] 在 `backend/tests/contract/test_cases_api.py` 新增 `preview_rf` contract test：`POST /api/v1/cases/preview-rf` 回傳 `{ rf_code: str }`；main_steps 為空時回傳 422；確認測試目前為 RED（端點尚未存在）
- [X] T119 [P] [US1] 建立 `frontend/tests/unit/StepsEditor.spec.ts`（RED stub）：測試 AI 補齊按鈕在 `mainSteps` 為空時為 disabled、點擊後呼叫 `caseApi.aiCompletePreview` 並 emit `update:mainSteps`；元件尚未存在，測試失敗為預期
- [X] T120 [P] [US1] 建立 `frontend/tests/unit/RFCodePreview.spec.ts`（RED stub）：測試翻譯按鈕觸發 `caseApi.previewRfCode`、loading 狀態顯示、翻譯失敗時顯示錯誤提示（不清空步驟）、程式碼預覽區渲染；元件尚未存在，測試失敗為預期

### 步驟二：後端實作（GREEN 階段）

- [X] T121 [US1] 在 `backend/src/api/cases.py` 新增 `POST /api/v1/cases/preview-rf` 端點（stateless）：接收 `{ main_steps: str, llm_model: str }` → 呼叫 AIService 生成 Robot Framework 語法 → 回傳 `{ rf_code: str }`；main_steps 為空或超過 10000 字元時回傳 422；timeout 設為 35s（對應 SC-010）；路由宣告於 `/{case_id}` 之前；不建立執行紀錄
- [X] T122 [P] [US1] 在 `frontend/src/services/caseApi.ts` 新增 `previewRfCode(payload: { main_steps: string; llm_model: string })` 方法，呼叫 `POST /api/v1/cases/preview-rf`

### 步驟三：前端元件實作（GREEN 階段）

- [X] T123 [US1] 建立 `frontend/src/components/StepsEditor/index.vue`：包含「主要步驟」`<textarea>`（required）、LLMModelSelector、「AI 補齊步驟」按鈕，透過 `v-model:mainSteps` 與 `v-model:selectedModel` 雙向綁定；AI 補齊邏輯移自 TestCaseForm，保持相同 API 呼叫（`caseApi.aiCompletePreview`）
- [X] T124 [P] [US1] 建立 `frontend/src/components/RFCodePreview/index.vue`：接受 `mainSteps` 與 `selectedModel` 作為 props；包含「翻譯為 Robot Framework」按鈕（點擊呼叫 `caseApi.previewRfCode`）、loading 狀態、`<pre><code>` 程式碼預覽區；翻譯失敗時顯示「翻譯失敗，請稍後重試」，不清除 mainSteps 內容
- [X] T125 [US1] 更新 `frontend/src/components/TestCaseForm/index.vue`：將「主要步驟」欄位改為接受 `mainSteps` prop（optional，預設空字串）並 emit `update:mainSteps`；當 prop 由父層傳入時父層控制，否則元件內部維護（**保持 CaseDetailPage 向後相容**，編輯頁不受影響）；移除 TestCaseForm 內的 AI bar（LLMModelSelector + AI 補齊按鈕）
- [X] T126 [US1] 重寫 `frontend/src/pages/CaseCreatePage.vue`：以 CSS Grid（`grid-template-columns: 1fr 1.4fr`）實作左右分割版面；左欄渲染 `<TestCaseForm>`（傳入 `mainSteps`/`selectedModel` v-model），右欄上方渲染 `<StepsEditor>`、下方渲染 `<RFCodePreview>`；`mainSteps` 與 `selectedModel` 狀態由 CaseCreatePage 持有並向下傳遞；在 `<768px` 時自動改為單欄（`grid-template-columns: 1fr`）

**Checkpoint**: `pytest backend/tests/contract/test_cases_api.py -k preview_rf` PASS；`npm run test` T118–T120 測試全數 GREEN；`npm run dev` 可見 CaseCreatePage 左右兩欄，右欄含步驟輸入、AI 補齊、翻譯為 RF 功能；CaseDetailPage 編輯功能不受影響

---

## Phase 12: AI Chat 介面 — Tab 分頁重構（FR-001，2026-05-29）

**Purpose**: 將建立／編輯測試案例畫面重構為 Tab 分頁；Tab 2「測試步驟」實作 AI Chat 多輪對話（左側）+ RF 程式碼自動預覽（右側）；對話歷史持久化至資料庫。

> **TDD 順序**：測試先寫（RED）→ 後端 DB/Model/Service/API → 前端 Service → 前端元件 → 頁面重構（GREEN）

### 步驟一：先寫測試（RED 階段）

- [X] T127 [P] [US1] 在 `backend/tests/contract/test_cases_api.py` 新增 `TestChatEndpoints` class：`POST /api/v1/cases/{id}/chat` 回傳 `{ assistant_message, rf_code }`；`GET /api/v1/cases/{id}/chat-history` 回傳 `{ messages: [] }`；確認目前為 RED（端點尚未存在）
- [X] T128 [P] [US1] 建立 `frontend/tests/unit/AIChatPanel.spec.ts`（RED stub）：測試聊天輸入框渲染、送出按鈕 disabled 狀態（空輸入時）、送出後呼叫 `caseApi.chatWithAI`、AI 回應以氣泡顯示、emit `rf-updated` 事件；元件尚未存在，測試失敗為預期

### 步驟二：後端 DB + Model（GREEN 階段）

- [X] T129 [US1] 建立 Alembic migration：新增 `case_chat_messages` 資料表（id UUID PK, case_id FK→test_cases, role VARCHAR('user'/'assistant'), content TEXT, created_at DATETIME）；執行 `alembic upgrade head`
- [X] T130 [P] [US1] 建立 `backend/src/models/case_chat_message.py`：`CaseChatMessage` SQLAlchemy ORM model，`role` 欄位限定 'user'/'assistant'，與 `TestCase` 建立 `relationship`

### 步驟三：後端 Service + API（GREEN 階段）

- [X] T131 [US1] 在 `backend/src/services/ai_service.py` 新增 `chat_and_generate_rf(messages: list, user_message: str, llm_model: str) -> dict`：將歷史訊息組裝成 LLM context，送出多輪對話請求，解析回應同時生成 RF 程式碼，回傳 `{ assistant_message: str, rf_code: str }`；timeout 35s
- [X] T132 [P] [US1] 在 `backend/src/api/cases.py` 新增 `POST /cases/{id}/chat`：讀取現有對話歷史，呼叫 `ai_service.chat_and_generate_rf()`，將 user/assistant 訊息寫入 `case_chat_messages`，回傳 `{ assistant_message, rf_code }`；路由宣告須在 `/{case_id}` 模板路由之前
- [X] T133 [P] [US1] 在 `backend/src/api/cases.py` 新增 `GET /cases/{id}/chat-history`：從 DB 讀取該 case 的所有 `CaseChatMessage`（依 created_at 排序），回傳 `{ messages: [{ role, content, created_at }] }`

### 步驟四：前端 Service + 元件（GREEN 階段）

- [X] T134 [P] [US1] 在 `frontend/src/services/caseApi.ts` 新增 `chatWithAI(caseId: string, message: string, model: string)` → `POST /cases/{id}/chat`；`getChatHistory(caseId: string)` → `GET /cases/{id}/chat-history`
- [X] T135 [US1] 建立 `frontend/src/components/AIChatPanel/index.vue`：左側 Chat 氣泡介面（user 訊息靠右藍色，assistant 訊息靠左灰色），底部輸入框 + 送出按鈕（空輸入或 loading 時 disabled），送出後呼叫 `caseApi.chatWithAI`，AI 回應後 emit `rf-updated` 事件並傳遞 `rf_code`；props: `caseId?: string`、`selectedModel: string`；載入時若有 `caseId` 則呼叫 `getChatHistory` 還原歷史訊息

### 步驟五：頁面重構（GREEN 階段）

- [X] T136 [US1] 重寫 `frontend/src/pages/CaseCreatePage.vue`：採 Tab 分頁結構（Tab 1「基本資訊」→ TestCaseForm + 儲存按鈕；Tab 2「測試步驟」→ AIChatPanel（左）+ RFCodePreview（右）左右分割 `1fr 1.2fr`）；`selectedModel` 狀態由頁面持有；Tab 2 監聽 `rf-updated` 事件更新 RFCodePreview；RFCodePreview 在此模式下僅顯示，不再有翻譯按鈕（由 AIChatPanel 觸發自動更新）；`<768px` 改為單欄
- [X] T137 [US1] 重構 `frontend/src/pages/CaseDetailPage.vue` 編輯模式：與 CaseCreatePage 採相同 Tab 結構；開啟編輯時以 `caseId` 載入現有對話歷史；儲存成功後回到檢視模式；`caseId` 傳入 AIChatPanel

**Checkpoint**: `pytest backend/tests/contract/test_cases_api.py -k chat` PASS；`npm run test` T127–T128 GREEN；`npm run dev` 可見 CaseCreatePage Tab 分頁，Tab 2 左側 AI Chat 氣泡，右側 RF 自動更新；CaseDetailPage 編輯模式同樣 Tab 結構

---

## Phase 13: 測試清單版面重構（FR-006，2026-05-29）

**Purpose**: 將測試清單列表頁與詳情頁版面比照測試案例管理頁面（相同的條列式結構、搜尋篩選、詳情版面）。

> **TDD 順序**：測試先寫（RED）→ 頁面重構（GREEN）

### 步驟一：先寫測試（RED 階段）

- [X] T138 [P] [US3] 建立 `frontend/tests/unit/ChecklistsPage.spec.ts`（RED stub）：測試清單列表渲染、搜尋欄存在、清單項目可點擊；頁面尚未重構，若已有舊版本則測試新增的元素為 RED
- [X] T139 [P] [US3] 建立 `frontend/tests/unit/ChecklistDetailPage.spec.ts`（RED stub）：測試標題區、基本資訊區、清單案例列表、執行歷史區四個區塊存在

### 步驟二：頁面重構（GREEN 階段）

- [X] T140 [US3] 重構 `frontend/src/pages/ChecklistsPage.vue`：採用與 `CasesPage` 相同版面（頁面標題＋「建立清單」按鈕、搜尋欄、條列式清單表格（欄位：清單名稱、建立人員、案例數、最後執行時間、狀態）、空狀態提示；清單項目可點擊進入詳情頁
- [X] T141 [P] [US3] 重構 `frontend/src/pages/ChecklistDetailPage.vue`：採用與 `CaseDetailPage` 相同版面結構（頁首：清單名稱＋動作按鈕（執行測試／編輯）；基本資訊區：名稱、建立人員、建立時間；案例列表區：條列所含案例（名稱、系統別、順序）可移除；執行歷史區：比照 CaseDetailPage 的歷史紀錄表格）

**Checkpoint**: `npm run test` T138–T139 GREEN；`npm run dev` /checklists 與 /checklists/:id 版面與 /cases 系列一致

---

---

## Phase 14: 效能 SCs 驗收測試（SC-005/SC-007/SC-011/SC-012/SC-013，2026-06-13）

**Purpose**: 補充 `/speckit-analyze` 找出的 5 項效能 SC 缺乏可自動化執行的驗收測試（H3 remediation）

- [X] T142 [P] [US5] 建立 `backend/tests/load/test_report_generation_time.py`：執行一次含 5 個案例的 checklist 後，呼叫 `ReportService.export_report()`，斷言從呼叫到回傳 HTML 字串的時間 ≤ 30s（對應 SC-005）
- [X] T143 [P] [US1] 建立 `backend/tests/load/test_ai_complete_latency.py`：mock LLM provider 以固定 12s 延遲回應，呼叫 `AIService.complete_steps()`，斷言整體呼叫時間 ≤ 15s（對應 SC-007；mock 延遲設為 12s 以留出 3s 餘裕）
- [X] T144 [P] [US5] 建立 `backend/tests/load/test_trial_run_latency.py`：mock RF subprocess 以固定 50s 完成，呼叫 `ExecutionService.run_trial()`，斷言從觸發到回傳結果 ≤ 60s（對應 SC-011）
- [X] T145 [P] [US2] 建立 `backend/tests/load/test_file_parser_latency.py`：生成包含 1000 筆資料列的 Excel 檔案，呼叫 `FileParserService.parse_excel()`，斷言解析與預覽生成時間 ≤ 5s（對應 SC-012）
- [X] T146 [P] [US5] 建立 `backend/tests/load/test_results_page_latency.py`：建立含 50 筆 ExecutionMedia 的執行紀錄，呼叫 `GET /executions/{id}/results`，斷言回應時間 ≤ 10s（對應 SC-013）

**Checkpoint**: `pytest backend/tests/load/test_report_generation_time.py backend/tests/load/test_ai_complete_latency.py backend/tests/load/test_trial_run_latency.py backend/tests/load/test_file_parser_latency.py backend/tests/load/test_results_page_latency.py` 全數 PASS

---

## Phase 15: FR-023 清單 CRUD + 案例管理畫面 + pabot 整合（2026-06-20 新增）

**Purpose**: 實作本日 /speckit-clarify 新增的 FR-023（清單 CRUD、/checklists/:id/cases 案例管理畫面）及修補 speckit-analyze 找出的 3 項 CRITICAL：ExecutionListener RF Plugin、ChecklistItem.notes migration、CaseDetailPage 瀏覽模式 Tab 2

- [X] T147 [P] 更新 `backend/requirements.txt`：新增 `robotframework-pabot` 依賴（對應 plan.md 主要依賴更新，修補 F2）
- [X] T148 [US3] 執行 `alembic revision --autogenerate -m "add_checklist_item_notes"` 並驗證 `checklist_items` 表新增 `notes TEXT nullable` 欄位（對應 data-model.md ChecklistItem.notes，修補 E3）
- [X] T149 [P] [US3] 寫 contract test（TDD RED）：`backend/tests/contract/test_checklist_crud_api.py`（PUT /checklists/{id} 200、DELETE /checklists/{id} 200/409、GET /checklists/{id}/cases 200、POST /checklists/{id}/cases 201/409、DELETE /checklists/{id}/cases/{case_id} 200、PATCH /checklists/{id}/cases/{case_id} 200、PUT /checklists/{id}/cases/reorder 200）（修補 C1/C2）
- [X] T150 [P] [US5] 寫 unit test（TDD RED）：`backend/tests/unit/test_execution_listener.py`（ExecutionListener.start_test 寫入 Queue 的 case_started 事件、end_test 寫入 case_completed 事件含 status/elapsed_ms/message、Queue Registry get_execution_queue 建立並複用同 execution_id 的 Queue）（修補 E2）
- [X] T151 [US5] 建立 `backend/src/execution/listener.py`：ExecutionListener RF Plugin（ROBOT_LISTENER_API_VERSION = 2、`__init__(self, execution_id)`、start_test/end_test 回呼寫入 asyncio.Queue）+ Queue Registry（`_queues: dict[str, asyncio.Queue]`、`get_execution_queue(execution_id) -> asyncio.Queue`）（修補 E2，對應 research.md Decision 5）
- [X] T152 [US3] 完善 `backend/src/services/checklist_service.py`：新增 `update_checklist`（修改 name/created_by）、`delete_checklist`（409 guard：active executions 中止刪除）、`list_checklist_cases`（回傳 ChecklistItem + TestCase 摘要含 notes/position）、`add_case`（409 guard：已存在）、`remove_case`、`update_case_item`（notes 和/或 position）、`reorder_cases`（批次更新 position）（對應 FR-023）
- [X] T153 [US3] 完善 `backend/src/api/checklists.py`：掛載 FR-023 新端點：`PUT /{id}`、`DELETE /{id}`、`GET /{id}/cases`、`POST /{id}/cases`、`DELETE /{id}/cases/{case_id}`、`PATCH /{id}/cases/{case_id}`、`PUT /{id}/cases/reorder`（對應 contracts/api.md）
- [X] T154 [P] [US2] 更新 `frontend/src/pages/CaseDetailPage.vue`：瀏覽模式（非編輯路由）改為 Tab 結構—Tab 1「基本資訊」顯示完整欄位與版本歷史（唯讀）、Tab 2「測試步驟」顯示 AI 對話歷史（`GET /cases/{id}/chat-history`）與最新 RF 程式碼預覽（唯讀，複用 RFCodePreview 元件）（對應 FR-005 更新，修補 E1）
- [X] T155 [P] [US3] 建立 `frontend/src/pages/ChecklistCasesPage.vue`（/checklists/:id/cases 案例管理畫面）：顯示已加入案例列表（含 notes、position 可拖曳排序）、搜尋可加入的案例（呼叫 GET /cases）、加入按鈕（POST /cases）、移除按鈕（DELETE /cases/{case_id}）、備註欄位行內編輯（PATCH /cases/{case_id}）、排序拖曳後送出（PUT /cases/reorder）
- [X] T156 [US3] 在 `frontend/src/router/index.ts` 新增路由 `/checklists/:id/cases` → ChecklistCasesPage；在 `frontend/src/pages/ChecklistDetailPage.vue` 頁首新增「管理案例」按鈕（跳轉至 /checklists/:id/cases）、「編輯」按鈕（PUT /checklists/:id inline modal）、「刪除」按鈕（DELETE /checklists/:id，409 時顯示 "有執行中的測試，無法刪除"）（對應 FR-023 US3 AS-6~AS-11）

**Checkpoint**: `pytest backend/tests/contract/test_checklist_crud_api.py backend/tests/unit/test_execution_listener.py -v` GREEN；`npm run dev` /checklists/:id 顯示「管理案例」按鈕，/checklists/:id/cases 可正常新增/移除/排序案例

---

## Phase 16: 執行引擎修正 + RF 腳本持久化（2026-06-20）

**Purpose**: 修正 SSE session isolation 造成執行頁永遠顯示「error」的根因；建立 RF 腳本實體檔案持久化流程，使執行引擎能正確讀取 .robot 檔案。

- [X] T157 修正 `backend/src/api/executions.py` SSE polling：每次輪詢開啟獨立 `AsyncSessionLocal()` session（修正 SQLite WAL read-transaction snapshot 問題），timeout 延長至 120 輪，timeout event 欄位由 `error` 改為 `message`
- [X] T158 修正 `frontend/src/stores/executionStore.ts`：`execution_completed` handler 新增同步 `totalCases.value = (event.total as number) || totalCases.value` 及 `completedCases.value = totalCases.value`，確保進度數字正確
- [X] T159 [P] 在 `backend/src/api/cases.py` 新增 `PUT /{case_id}/robot-script`（接受 `rf_code: str`，寫入 `robot_scripts/{case_number}.robot`）與 `GET /{case_id}/robot-script`（讀取檔案回傳 `rf_code`，404 若不存在）
- [X] T160 更新 `backend/src/services/execution_service.py` `_execute_all_cases_bg`：先批次查 case_number，`run_one()` 內讀取 `robot_scripts/{case_number}.robot` 並將 `robot_code` 傳入 `_run_single_case_with_timeout()`
- [X] T161 重構 `frontend/src/components/RFCodePreview/index.vue`：新增 `caseId?: string` prop；新增「儲存 RF 程式碼」按鈕（`saving`/`saved`/`saveError` 狀態）；`onMounted` 若有 `caseId` 且無 override 則呼叫 `getRobotScript` 自動載入已儲存腳本
- [X] T162 [P] 在 `frontend/src/services/caseApi.ts` 新增 `saveRobotScript(caseId, rfCode)` 與 `getRobotScript(caseId)` 兩個 API 方法
- [X] T163 [P] 修正 `backend/src/repositories/test_case_repo.py` 清單案例搜尋邏輯：keyword 同時比對 `case_number LIKE` 與 `name LIKE`（OR 條件），修正 ChecklistCasesPage 搜尋只找到名稱而非編號的問題

**Checkpoint**: 執行清單後 ExecutionPage 正確顯示 `completed`；RFCodePreview 顯示「儲存 RF 程式碼」按鈕且可持久化；清單案例搜尋可依編號或名稱找到案例

---

## Phase 17: 剩餘未實作功能（待完成）

**Purpose**: 補齊 spec 中尚未實作的功能：測試案例列表伺服器端排序（FR-003）與 pabot 並行執行引擎整合（FR-015）。

### US1 — 測試案例列表排序（FR-003）

- [X] T164 [US1] 在 `backend/src/api/cases.py` `GET /cases` 端點新增 `sort_by: str = "created_at"` 與 `order: str = "desc"` query 參數，並傳入 repository 層；支援排序欄位：`case_number`、`name`、`created_at`、`updated_at`
- [X] T165 [P] [US1] 在 `backend/src/repositories/test_case_repo.py` `list()` 方法新增 `sort_by`/`order` 參數，對應 SQLAlchemy `order_by()` 動態排序（invalid column → fallback `created_at desc`）
- [X] T166 [P] [US1] 更新 `frontend/src/services/caseApi.ts` `listCases()` 型別新增 `sort_by?: string` 與 `order?: string` 參數
- [X] T167 [US1] 更新 `frontend/src/components/TestCaseList/index.vue` 表格標題列（案例編號、名稱、更新時間）改為可點擊排序；點擊後切換 `asc`/`desc`，顯示 ↑/↓ 指示符；重新呼叫 API 帶 `sort_by` 與 `order` 參數

**Checkpoint**: `GET /cases?sort_by=case_number&order=asc` 回傳正確排序；CasesPage 欄位標題可點擊並顯示排序指示符

### US5 — pabot 並行執行引擎（FR-015）

- [X] T168 [US5] 重構 `backend/src/services/execution_service.py` `_execute_all_cases_bg`：改用 `pabot --processes {max_workers}` 執行所有 .robot 檔案（max_workers>1 時），解析 pabot output.xml 更新各案例 pass/fail 狀態；單案例保留 per-case asyncio 架構
- [X] T169 [P] [US5] SSE 改由 `get_execution_queue(execution_id)` 讀取即時事件（`case_started`/`case_completed`/`execution_completed`），background task 直接 put_nowait 至 Queue；保留 5 秒週期 DB 輪詢作為 fallback；`clear_execution_queue` 在執行後 5 秒清理

**Checkpoint**: 執行含多案例清單時，pabot 並行啟動，SSE 即時推送每個案例狀態；`pytest backend/tests/unit/test_execution_listener.py -v` GREEN

### FR-022 — 行動裝置漢堡選單

- [X] T170 [US3] 更新 `frontend/src/App.vue` 全域導覽列：在 `<768px` 媒體查詢下自動收合，新增漢堡按鈕（☰）切換展開/收合狀態，確保行動裝置可正常操作所有導覽連結（對應 FR-022 行動裝置支援）

**Checkpoint**: 瀏覽器縮至 < 768px 時導覽列顯示 ☰ 按鈕，點擊後展開完整導覽項目

### SC-006 — 並發用戶壓力測試

- [X] T171 [P] 建立 `backend/tests/load/test_concurrent_users.py`：模擬 10 個並發 session 同時呼叫 `GET /cases`（各 1 頁 / 千筆資料集），斷言 p95 回應時間 ≤ 2s（對應 SC-006）

**Checkpoint**: `pytest backend/tests/load/test_concurrent_users.py -v` GREEN

### SC-009 — 平行執行效能 benchmark（依賴 T168）

- [X] T172 [US5] 建立 `backend/tests/load/test_parallel_vs_sequential.py`：以 10 個 mock .robot 檔（各模擬 3s 執行時間）分別計算 pabot 並行 vs 逐案循序執行時間，斷言並行執行時間 ≤ 循序時間 × 60%（即縮短 ≥ 40%，對應 SC-009）；此測試依賴 T168 完成

**Checkpoint**: `pytest backend/tests/load/test_parallel_vs_sequential.py -v` GREEN（需先完成 T168）

### FR-017 — 試跑紀錄 30 天自動清除

- [X] T173 在 `backend/src/main.py` startup event 新增 `asyncio.create_task(_cleanup_trial_runs())`；`_cleanup_trial_runs()` 每日 00:00 UTC 軟刪除 `execution_records WHERE execution_type='trial_run' AND created_at < NOW()-30days`（對應 FR-017 試跑紀錄保留 30 天）

**Checkpoint**: 手動設定 `created_at` 超過 30 天的 trial_run 紀錄，呼叫清除函式後確認紀錄已標記刪除

---

---

## Phase 18: RF 原生報告嵌入 + 排序補齊（2026-06-20）

**Purpose**: 實作 FR-010/FR-019：RF 執行後持久化 log.html/report.html，在結果頁面以「RF 報告」Tab + iframe 方式嵌入；同時補齊 FR-003 `system_category` 排序欄位（speckit-analyze I3 問題）。

### US4 — RF 原生報告嵌入（FR-010 / FR-019）

- [X] T174 在 `backend/src/core/config.py` `Settings` 類別新增 `execution_reports_dir: str = "data/execution_reports"`；在 `backend/src/main.py` startup event 新增 `os.makedirs(settings.execution_reports_dir, exist_ok=True)` 確保目錄存在
- [X] T175 修改 `backend/src/services/execution_service.py` `_run_pabot`：在 `with tempfile.TemporaryDirectory() as tmp_dir:` block 結束前（output_dir 存在時）呼叫 `import shutil; shutil.copytree(output_dir, os.path.join(settings.execution_reports_dir, execution_id), dirs_exist_ok=True)` 持久化 RF 原生報告
- [X] T176 [P] 修改 `backend/src/services/execution_service.py` `_run_single_case_with_timeout` 與 `_execute_robot_subprocess`：新增 `execution_id: Optional[str] = None` 參數；在 `with tempfile.TemporaryDirectory() as tmp_dir:` block 結束前，若 `execution_id` 不為 None 則 `shutil.copytree(tmp_dir, os.path.join(settings.execution_reports_dir, execution_id), dirs_exist_ok=True)`；更新 `_execute_trial_bg` 傳入 `execution_id=execution_id`
- [X] T177 [P] 在 `backend/src/api/executions.py` 新增 `GET /executions/{execution_id}/rf-report/{filename:path}` 端點：回傳 `FileResponse(os.path.join(settings.execution_reports_dir, execution_id, filename))`，若路徑不存在回傳 `404 {"detail": "報告尚未生成或不存在"}`；需 `from fastapi.responses import FileResponse`
- [X] T178 更新 `frontend/src/pages/ResultPage.vue`：新增「RF 報告」主 Tab（與現有「執行結果」並列）；Tab 內含兩個子 Tab 按鈕「執行日誌」/ 「測試報告」，切換時各以 `<iframe style="width:100%;height:80vh;border:none" :src="\`/api/v1/executions/${executionId}/rf-report/log.html\`">` 或 `report.html` 嵌入；若執行 `status` 非 `completed`/`failed` 則顯示「執行進行中，報告生成後可查閱」提示

**Checkpoint**: 執行完一個含 RF 腳本的清單後，`data/execution_reports/{id}/log.html` 存在；開啟結果頁點擊「RF 報告」Tab 顯示 RF 原生 log.html iframe；切換子 Tab 可查閱 report.html

### US1 補強 — 排序欄位補齊（FR-003 / speckit-analyze I3）

- [X] T179 [P] 修正 `backend/src/api/cases.py` `GET /cases`：在 `sort_by` query 參數允許值中新增 `"system_category"`；修正 `backend/src/repositories/test_case_repo.py` `list()` 方法：`sort_by == "system_category"` 時對應 `TestCase.system_category` 欄位排序（修補 FR-003 spec 要求但 T164 未實作的缺口）
- [X] T180 [P] 更新 `frontend/src/components/TestCaseList/index.vue`：表格標題新增「系統類別」欄位並支援可點擊排序（`sort_by: "system_category"`），與現有 case_number/name/updated_at 排序欄位保持一致的 ↑/↓ 指示符邏輯

**Checkpoint**: `GET /cases?sort_by=system_category&order=asc` 回傳依系統類別排序的結果；CasesPage 顯示「系統類別」欄位標題且可點擊排序

---

---

## Phase 19: version 欄位排序 + checklists 列表排序（2026-06-20）

**Purpose**: 依最新 clarification 實作 FR-003 第五排序欄（`version`）與 FR-006 清單列表後端排序（`name`、`created_by`、`created_at`）。

### US1 — version 欄位排序（FR-003）

- [X] T181 [US1] 在 `backend/src/api/cases.py` `GET /cases` 的 `sort_by` 允許值中新增 `"version"`；在 `backend/src/repositories/test_case_repo.py` `list()` 方法加入 `sort_by == "version"` → `TestCase.version` 欄位排序
- [X] T182 [P] [US1] 更新 `frontend/src/pages/CasesPage.vue` 或 `frontend/src/components/TestCaseList/index.vue`：表格標題新增「版本」欄位（`sort_by: "version"`），與現有排序欄位保持相同的 ↑/↓ 指示符邏輯

**Checkpoint**: `GET /cases?sort_by=version&order=asc` 回傳依版本遞增排序；CasesPage 版本欄標題可點擊並顯示排序指示符

### US3 — checklists 列表後端排序（FR-006）

- [X] T183 [US3] 在 `backend/src/api/checklists.py` `GET /checklists` 端點新增 `sort_by: str = "created_at"` 與 `order: str = "desc"` query 參數，傳入 service/repository；在 `backend/src/repositories/checklist_repo.py` 加入動態排序邏輯（支援 `name`、`created_by`、`created_at`；invalid column → fallback `created_at desc`）
- [X] T184 [P] [US3] 更新 `frontend/src/services/checklistApi.ts` `listChecklists()` 新增 `sort_by?: string` 與 `order?: string` 參數
- [X] T185 [US3] 更新 `frontend/src/pages/ChecklistsPage.vue`：表格標題「清單名稱」、「建立人員」、「建立時間」改為可點擊排序，顯示 ↑/↓ 指示符，重新呼叫 API 帶 `sort_by`/`order`；預設 `created_at desc`

**Checkpoint**: `GET /checklists?sort_by=name&order=asc` 回傳依名稱排序；ChecklistsPage 三欄標題可點擊並顯示排序指示符

---

---

## Phase 20: 登入畫面 + 管理後台（FR-024〜FR-027）（2026-06-21）

**Purpose**: 新增 JWT 身份驗證、三角色 RBAC（admin/editor/viewer）、管理後台（帳號 CRUD、系統別 CRUD、LLM API Key 管理）。

### 後端基礎層（安全模組 + 模型 + 遷移）

- [X] T186 更新 `backend/requirements.txt` 加入 `python-jose[cryptography]` 與 `passlib[bcrypt]`；更新 `backend/.env.example` 新增 `JWT_SECRET_KEY`、`JWT_EXPIRE_HOURS=8`、`ADMIN_USERNAME`、`ADMIN_PASSWORD`；更新 `backend/src/core/config.py` Settings 暴露這四個欄位
- [X] T187 建立 `backend/src/core/security.py`：`create_access_token(sub, role)` → HS256 JWT（`python-jose`）；`decode_token(token)` → payload dict；`hash_password(plain)` / `verify_password(plain, hashed)` → passlib bcrypt；`OAuth2PasswordBearerCustom` scheme（token from Authorization header）
- [X] T188 建立 `backend/src/models/user.py`（User ORM：id UUID, username VARCHAR UNIQUE NOT NULL, hashed_password TEXT NOT NULL, role ENUM('admin','editor','viewer') DEFAULT 'viewer', is_active BOOL DEFAULT TRUE, created_at）；在 `backend/alembic/env.py` import User
- [X] T189 [P] 建立 `backend/src/models/system_category.py`（SystemCategory ORM：id UUID, name VARCHAR UNIQUE NOT NULL, is_deleted BOOL DEFAULT FALSE, created_at）；在 `backend/alembic/env.py` import SystemCategory
- [X] T190 [P] 建立 `backend/src/models/app_setting.py`（AppSetting ORM：id UUID, key VARCHAR UNIQUE NOT NULL, encrypted_value TEXT, updated_at）；在 `backend/alembic/env.py` import AppSetting
- [X] T191 執行 `alembic revision --autogenerate -m "add_user_system_category_app_setting"` 並驗證 migration upgrade 正常（新增 users / system_categories / app_settings 三張表）

### 後端 Repository + Service + Dependency

- [X] T192 建立 `backend/src/repositories/user_repo.py`：`get_by_username(username)`, `get(id)`, `list_all()`, `create(username, hashed_pw, role)`, `update(id, **fields)`, `set_active(id, is_active)`
- [X] T193 [P] 建立 `backend/src/repositories/system_category_repo.py`：`list_active()`, `get_by_name(name)`, `create(name)`, `update_name(id, name)`, `soft_delete(id)`, `count_cases_using(name)` (query TestCase.system_category == name where not is_deleted)
- [X] T194 [P] 建立 `backend/src/repositories/app_setting_repo.py`：`get(key)`, `set(key, value)` — value 以 `security.py` 的 AES-256（`cryptography` Fernet）加密後存入 encrypted_value
- [X] T195 更新 `backend/src/core/dependencies.py` 新增三個 dependency：`get_current_user(token=Depends(oauth2_scheme), db=Depends(get_db)) -> User`（decode JWT → 查 DB → 驗 is_active）；`require_admin(user=Depends(get_current_user)) -> User`（role != 'admin' → 403）；`require_editor_or_above(user=Depends(get_current_user)) -> User`（role == 'viewer' → 403）
- [X] T196 建立 `backend/src/services/auth_service.py`：`login(username, password, db)` → 查 User → verify_password → create_access_token → 回傳 `{access_token, token_type, role, username}`
- [X] T197 [P] 建立 `backend/src/services/user_service.py`：`create(username, plain_pw, role)` → hash_password → user_repo.create；`update_role(id, role)`；`set_active(id, is_active)`；`reset_password(id, new_pw)` → hash + update；`list_all()`；`delete(id)`（硬刪除，須先確認非當前登入使用者）
- [X] T198 [P] 建立 `backend/src/services/system_category_service.py`：`list()`, `create(name)`（重複 name → ValueError）, `rename(id, name)`, `delete(id)` → 先 `count_cases_using` 回傳影響數量，再 `soft_delete`；回傳 `{deleted: bool, affected_case_count: int}`
- [X] T199 [P] 建立 `backend/src/services/app_setting_service.py`：`get_llm_keys()` → 回傳 `{anthropic_key_set: bool, openai_key_set: bool}`（不回傳明文）；`set_llm_key(provider: "anthropic"|"openai", key: str)` → encrypt + upsert；`get_decrypted_key(provider)` → 供 LLMProvider 取用

### 後端 API 路由

- [X] T200 建立 `backend/src/api/auth.py`：`POST /auth/login` body `{username, password}` → 呼叫 auth_service.login → 回傳 `{access_token, token_type: "bearer", role, username}`；無 `Depends(get_current_user)`（公開端點）；掛載於 `backend/src/main.py` prefix `/api/v1`
- [X] T201 建立 `backend/src/api/admin.py`（所有端點均 `Depends(require_admin)`）：帳號管理 `GET /admin/users`, `POST /admin/users`, `PUT /admin/users/{id}`, `DELETE /admin/users/{id}`；系統別管理 `GET /admin/system-categories`, `POST /admin/system-categories`, `PUT /admin/system-categories/{id}`, `DELETE /admin/system-categories/{id}`（response 含 `affected_case_count`）；LLM Key 管理 `GET /admin/llm-keys`, `PUT /admin/llm-keys/{provider}`；掛載於 `backend/src/main.py` prefix `/api/v1`
- [X] T202 在 `backend/src/api/cases.py`、`backend/src/api/checklists.py`、`backend/src/api/executions.py`、`backend/src/api/db_connections.py` 的各端點 Depends 中加入 `current_user: User = Depends(get_current_user)`；寫入/刪除操作額外加入 `Depends(require_editor_or_above)`

### 後端 Seed Script

- [X] T203 建立 `backend/scripts/seed_admin.py`（`python -m scripts.seed_admin`）：讀取 `settings.ADMIN_USERNAME` / `settings.ADMIN_PASSWORD` → 檢查 username 是否已存在 → 不存在則建立 role='admin' 帳號；輸出成功或跳過訊息

### 前端認證層

- [X] T204 建立 `automatic_test/frontend/src/stores/authStore.ts`（Pinia）：state: `token: string|null`, `role: string|null`, `username: string|null`；actions: `login(username, password)` → POST /auth/login → 儲存 token/role/username 至 localStorage；`logout()` → 清除 localStorage + 跳轉 /login；`initFromStorage()` → 頁面載入時從 localStorage 還原 state；getter: `isAdmin`, `isEditor`, `isLoggedIn`
- [X] T205 更新 `automatic_test/frontend/src/services/apiClient.ts`：request interceptor 從 authStore 取 token，加入 `Authorization: Bearer {token}` header；response interceptor 攔截 401 → 呼叫 authStore.logout()（自動跳至 /login）
- [X] T206 建立 `automatic_test/frontend/src/pages/LoginPage.vue`：username + password input、登入按鈕、錯誤訊息（帳號或密碼錯誤）；成功後 authStore.login() 並導向 `/`；頁面無需 auth guard（/login 為公開頁）
- [X] T207 更新 `automatic_test/frontend/src/router/index.ts`：新增 `/login` 路由（component: LoginPage, meta: { requiresAuth: false }）；新增 `/admin` 路由（component: AdminPage, meta: { requiresAuth: true, requiresAdmin: true }）；`beforeEach` guard：無 token → 導向 /login；有 token 但 role != 'admin' 且目的地有 requiresAdmin → 導向 /（403 提示）；`authStore.initFromStorage()` 在 app 初始化時呼叫（`frontend/src/main.ts`）

### 前端管理後台

- [X] T208 建立 `automatic_test/frontend/src/services/adminApi.ts`：帳號 CRUD（listUsers, createUser, updateUser, deleteUser）；系統別 CRUD（listSystemCategories, createSystemCategory, renameSystemCategory, deleteSystemCategory）；LLM Key（getLlmKeyStatus, setLlmKey）
- [X] T209 建立 `automatic_test/frontend/src/pages/AdminPage.vue`：三個 Tab（「帳號管理」、「系統別管理」、「LLM API Keys」）；帳號管理 Tab：可新增帳號（username/password/role）、修改角色、重設密碼、停用/啟用、刪除；系統別管理 Tab：顯示所有系統別、可新增、重新命名、刪除（刪除前顯示影響案例數）；LLM API Keys Tab：顯示 anthropic/openai key 是否已設定（遮罩），可輸入新 key 覆寫
- [X] T210 更新 `automatic_test/frontend/src/App.vue`（全域導覽列）：右側新增使用者名稱顯示與「登出」按鈕（呼叫 authStore.logout()）；若 isAdmin 則顯示「管理後台」導覽連結（指向 /admin）

**Checkpoint**: 未登入時所有頁面導向 /login；登入後顯示使用者名稱與登出按鈕；admin 可存取 /admin 並完成帳號 / 系統別 / LLM Key 管理；viewer 登入後只能瀏覽與執行測試，無法新增/編輯

---

---

## Phase 22: 執行前空清單驗證（FR-009 pre-flight）（2026-06-21）

**Purpose**: 點擊「執行測試」前，前端驗證清單是否有案例；若為空顯示警示並阻擋請求

### 實作

- [X] T211 [US3] 修改 `automatic_test/frontend/src/pages/ChecklistDetailPage.vue` 的「執行測試」按鈕 click handler：執行前先讀取目前清單的案例數量（`checklist.items?.length` 或已載入的 `caseItems.length`），若 `=== 0` 則呼叫 `alert('測試清單為空，請先新增案例')` 並 `return`，不觸發 `executeChecklist` API 呼叫

**Checkpoint**: 清單無案例時點擊「執行測試」顯示 alert，Network tab 無 POST `/execute` 請求；清單有案例時行為不變

---

## Phase 23: LLM 設定 env-only + 後台唯讀遮罩（FR-027 / FR-012）（2026-06-21）

**Purpose**: `/admin` LLM 分頁唯讀顯示金鑰遮罩與目前預設模型；金鑰與預設模型一律由 `.env` 配置，建立案例表單採用全域預設值

> **設計修訂（2026-06-21，env-only）**：本 Phase 最終實作改為 **env-only**——金鑰與預設模型皆由 `.env` 配置、後台**唯讀**遮罩顯示，**移除** DB 持久化、模型下拉、金鑰寫入與所有 PUT 端點。下列 T212–T224 任務描述中涉及「DB / app_setting 持久化、set_default_model、模型下拉、PUT 端點」之部分，已依此修訂簡化；最終以程式碼與 plan.md Phase 23（env-only）為準。對應測試亦已調整為 env-only（唯讀端點、讀 env 遮罩、不存在 PUT）。

### TDD 測試（先寫、確認 RED）

- [X] T212 [P] 寫 unit test：`automatic_test/backend/tests/unit/test_app_setting_service.py`：`_mask()` 規則（前 7 字元 + `****…` + 末 4 碼；`len < 12` 整串 `****`；空值/None 處理）、`get_llm_keys()` 回傳遮罩且**不含完整明文**、`get_default_model()` / `set_default_model()` round-trip
- [X] T213 [P] 寫 contract test：`automatic_test/backend/tests/contract/test_admin_llm_api.py`：`GET /llm-keys` 回傳 `{*_key_set, *_key_masked}` 且無明文；`PUT /admin/llm-default-model` 寫入後 `GET` 取回一致；`GET`/`PUT` 非 admin → 403
- [X] T214 [P] 寫 unit test：`automatic_test/backend/tests/unit/test_llm_models_default.py`：`/llm-models` 的 `default` 在 app_setting 有值時回 DB 值、無值時 fallback `settings.default_llm_model`
- [X] T215 [P] 寫 frontend unit test：`automatic_test/frontend/tests/unit/AdminPage.spec.ts`：LLM 分頁已設定時顯示遮罩值、未設定顯示「未設定」、全域預設模型下拉變更後呼叫 `setDefaultModel`

### 後端實作

- [X] T216 [P] 修改 `automatic_test/backend/src/services/app_setting_service.py`：新增 `_mask(key: str) -> str` helper（輸出**前 7 字元 + `****…` + 末 4 碼**，如 `sk-ant-****…dF3a`；`len(key) < 12` 時整串以 `****` 取代；空值回空字串）；修改 `get_llm_keys()` 解密後回傳 `{anthropic_key_set, anthropic_key_masked, openai_key_set, openai_key_masked}`，**嚴禁回傳完整明文**
- [X] T217 修改 `automatic_test/backend/src/services/app_setting_service.py`：新增 `get_default_model() -> str | None`（讀 key=`default_llm_model`，沿用 `repo.get_decrypted`）與 `set_default_model(model_id: str)`（沿用 `repo.set`，存於 `encrypted_value`，無需 migration；加結構化日誌記錄變更，符合 constitution「Structured logging」）
- [X] T218 修改 `automatic_test/backend/src/api/admin.py`：`GET /llm-keys` 回傳含遮罩值（沿用 T216 結構）；新增 `GET /admin/llm-default-model`（無設定則回 env 預設）與 `PUT /admin/llm-default-model`（body `{model: str}`，呼叫 `set_default_model` 並 `commit`），均加 `Depends(require_admin)`
- [X] T219 修改 `automatic_test/backend/src/api/llm_models.py`：`list_llm_models` 改為 `async` 並注入 `Depends(get_db)`；回傳的 `default` 改為 **DB 優先**（讀 `AppSettingService.get_default_model()`），無值時 fallback 至 `settings.default_llm_model`
- [X] T220 修改 LLM 呼叫端（AI 補齊 / Chat / RF 代碼生成 service，先 grep 定位所有後端呼叫點）：當請求未顯式指定模型時，改以全域預設模型（`AppSettingService.get_default_model()`，無則 env）為準

### 前端實作

- [X] T221 [P] 修改 `automatic_test/frontend/src/services/adminApi.ts`：`LlmKeyStatus` 型別新增 `anthropic_key_masked?: string`、`openai_key_masked?: string`；新增 `getDefaultModel(): Promise<{ model: string }>` 與 `setDefaultModel(model: string): Promise<void>`（對應 T218 端點）
- [X] T222 修改 `automatic_test/frontend/src/pages/AdminPage.vue` LLM 分頁：已設定時於狀態列顯示遮罩值（如 `目前：sk-ant-****…dF3a`），未設定顯示「未設定」；新增「全域預設模型」下拉（選項來源 `/llm-models`，**僅列 `requires_setup=false` 的可用模型**，標示目前值），變更後呼叫 `adminApi.setDefaultModel` 儲存並顯示成功訊息
- [X] T223 修改 `automatic_test/frontend/src/pages/CaseCreatePage.vue`：移除寫死的 `const selectedModel = ref('claude-sonnet-4-6')`，改於 `onMounted` 呼叫 `/llm-models` 取得 `default` 後賦值；表單不新增任何模型選擇器
- [X] T224 [P] 刪除前端死碼：移除 `automatic_test/frontend/src/components/StepsEditor/` 與 `automatic_test/frontend/src/components/LLMModelSelector/`（全前端零引用，先以 grep 確認無 import 後刪除）

**Checkpoint**: TDD 測試（T212–T215）先寫並確認 RED；實作後 `/admin` LLM 分頁載入即顯示已設定 key 的遮罩、API 回應不含明文；切換全域預設模型並儲存後新建案例的 AI 補齊即採用該模型（無需重啟）；建立案例頁無模型選擇器且不再寫死模型

**Dependencies**: TDD（T212–T215）先寫並確認 RED → 再實作。T218 依賴 T216+T217；T219、T220 依賴 T217；T222 依賴 T221+T218；T223 依賴 T219。可平行起步：T212–T215（測試）、T216/T221/T224

---

## Phase 24: 本地 Ollama 整合 + 後台「目前啟用模型」可切換（FR-012 / FR-027）（2026-06-21）

**Purpose**: 新增本地 Ollama provider（原生 `/api/chat`）；後台改為可選「目前使用模型」（跨 Claude/OpenAI/Ollama、僅列可用、存 DB 即時生效）；金鑰／連線維持 `.env` 唯讀

> **與 Phase 23 關係**：金鑰／`OLLAMA_BASE_URL` 維持 `.env` 唯讀；僅「目前啟用模型」由唯讀改回 DB 可切換（部分修訂 Phase 23）。

### TDD 測試（先寫、確認 RED）

- [X] T225 [P] 寫 unit test：`automatic_test/backend/tests/unit/test_ollama_provider.py`：mock `httpx` `POST {base}/api/chat`（`stream:false`）回應，驗證 `OllamaProvider.complete` / `complete_with_messages` 正確解析 `message.content`、模型名去除 `ollama:` 前綴
- [X] T226 [P] 寫 test：`automatic_test/backend/tests/unit/test_llm_models_ollama.py`：mock `GET {base}/api/tags`，驗證 `/llm-models` 列出 `ollama:<name>` 並帶 `provider="ollama"`、`requires_setup=false`；Ollama 連線失敗/逾時時 Ollama 區塊為空且不影響雲端模型
- [X] T227 [P] 寫 contract test：`automatic_test/backend/tests/contract/test_active_model_api.py`：`GET /admin/active-model`、`PUT /admin/active-model` 寫入後 `GET` 一致且 `/llm-models` 的 `default` 反映；非 admin → 403；未帶 token → 401
- [X] T228 [P] 更新 frontend unit test：`automatic_test/frontend/tests/unit/AdminPage.spec.ts`：金鑰維持唯讀遮罩；新增「目前使用模型」下拉，變更後呼叫 `setActiveModel`；下拉僅含可用模型

### 後端實作

- [X] T229 修改 `automatic_test/backend/src/core/config.py`：新增 `ollama_base_url: str = ""`（對應 env `OLLAMA_BASE_URL`）
- [X] T230 修改 `automatic_test/backend/src/core/llm_provider.py`：新增 `OllamaProvider`（以 `httpx.AsyncClient` POST `{ollama_base_url}/api/chat`，`stream:false`，解析 `message.content`；實作 `complete`/`complete_with_messages`；`complete_with_vision` 退化為純文字）；`get_provider` 改三方路由：`startswith("ollama:")`→`OllamaProvider`（去前綴）、`startswith("claude")`→Anthropic、其餘→OpenAI
- [X] T231 修改 `automatic_test/backend/src/services/app_setting_service.py`：恢復 `db`/`AppSettingRepository`（混合式：金鑰仍讀 env、啟用模型讀寫 DB）；新增 `get_active_model()`（沿用 `repo.get_decrypted(key="active_llm_model")`；無則回 `settings.default_llm_model`）與 `set_active_model(model_id)`（`repo.set(...)`，沿用既有加密欄、無 migration）；`get_llm_keys` 增列 Ollama 連線狀態欄位（`ollama_base_url` + 是否設定）
- [X] T232 修改 `automatic_test/backend/src/api/llm_models.py`：以 async `httpx` 查 `{ollama_base_url}/api/tags`（設定逾時、失敗則略過），將已安裝模型併入清單（id=`ollama:<name>`, provider="ollama", requires_setup=false）；雲端模型標 `provider`/`requires_setup`；`default` 改回傳 `AppSettingService(db).get_active_model()`
- [X] T233 修改 `automatic_test/backend/src/api/admin.py`：新增 `GET /admin/active-model`（回目前啟用模型）與 `PUT /admin/active-model`（body `{model}`→`set_active_model`+`commit`，即時生效），均 `Depends(require_admin)`
- [X] T234 修改 `automatic_test/backend/src/api/cases.py`：4 處 LLM 呼叫未指定模型時改用 `AppSettingService(session).get_active_model()`（取代 `settings.default_llm_model`）
- [X] T235 修改 `automatic_test/backend/.env` 與 `.env.example`：新增 `OLLAMA_BASE_URL=http://localhost:11434`（含註解）

### 前端實作

- [X] T236 [P] 修改 `automatic_test/frontend/src/services/adminApi.ts`：新增 `getActiveModel()`、`setActiveModel(model)`、`getLlmModels()`（回 `{ models:[{id,name,provider,requires_setup}], default }`）
- [X] T237 修改 `automatic_test/frontend/src/pages/AdminPage.vue` LLM 分頁：金鑰維持唯讀遮罩並顯示 Ollama 連線狀態；新增「目前使用模型」下拉（依 provider 分組、僅列 `requires_setup=false`），變更即呼叫 `setActiveModel` 並提示成功
- [X] T238 修改 `automatic_test/frontend/src/pages/CaseCreatePage.vue`：確認 `onMounted` 讀 `/llm-models` 的 `default`（即目前啟用模型）；無需模型選擇器

**Checkpoint**: TDD（T225–T228）先 RED；`.env` 設 `OLLAMA_BASE_URL` 後 `/llm-models` 列出 `ollama:*`，Ollama 離線則略過、雲端不受影響；後台選任一可用模型（含 `ollama:gemma4:e4b`）即時生效、新建案例 AI 補齊採用之、無需重啟；金鑰仍 `.env` 唯讀、後台不可編輯

**Dependencies**: TDD（T225–T228）先寫確認 RED → 再實作。T230 依賴 T229；T232 依賴 T230+T231；T233、T234 依賴 T231；T237 依賴 T236+T232+T233。可平行起步：T225–T228（測試）、T229/T236

---

## Phase 25: 測資變數四欄表格 + 清單案例展開列（FR-001 / FR-005 / FR-006 / FR-023）（2026-07-04）

**Purpose**: 依 2026-07-04 clarification 實作兩項新功能：（1）TestData 補充 rf_variable（RF 變數）與 description（說明）欄位，前端 Tab 1「基本資訊」改以四欄表格呈現測資（易讀名稱 / RF 變數 / 預設值 / 說明）；（2）清單詳情頁（/checklists/:id）案例列新增展開/收合，展開後顯示含「實際值」的四欄測資表格，實際值持久化於 ChecklistItem.actual_values。

### TDD 測試（先寫、確認 RED）

- [X] T239 [P] [US1] 寫 contract test：`backend/tests/contract/test_test_data_api.py`（POST /cases 含 test_data 陣列的 rf_variable/description 欄位；GET /cases/:id 回傳 test_data 含四欄 field_name/rf_variable/field_value/description；PATCH /cases/:id/test_data/:td_id 接受 rf_variable/description 更新）
- [X] T240 [P] [US3] 寫 contract test：`backend/tests/contract/test_checklist_actual_values.py`（GET /checklists/:id/cases 每個 item 含 test_data 陣列（四欄）與 actual_values dict；PATCH /checklists/:id/cases/:case_id body 傳入 `actual_values: {rf_var: value}` 回傳 200 含更新後 actual_values；非法 case_id → 404）

### 資料庫 Migration

- [X] T241 [US1] 執行 `alembic revision --autogenerate -m "add_test_data_rf_variable_description_checklist_actual_values"` 並驗證 upgrade/downgrade：`test_data` 表新增 `rf_variable VARCHAR(200) nullable` 與 `description TEXT nullable`；`checklist_items` 表新增 `actual_values TEXT nullable`（JSON 序列化儲存）

### 後端 Model 更新

- [X] T242 [P] [US1] 更新 `backend/src/models/test_data.py`：新增 `rf_variable = Column(String(200), nullable=True)` 與 `description = Column(Text, nullable=True)` 兩欄
- [X] T243 [P] [US3] 更新 `backend/src/models/checklist_item.py`：新增 `actual_values = Column(Text, nullable=True)`（存 JSON 字串，讀取時 `json.loads`，寫入時 `json.dumps`）

### 後端 API 更新

- [X] T244 [US1] 更新 `backend/src/api/cases.py`：TestDataCreate / TestDataUpdate request schema 新增 `rf_variable: str | None` 與 `description: str | None`；TestDataOut response schema 補充四欄；create/update 時若 `rf_variable` 為空則自動帶入 `"${" + field_name + "}"`；service/repo 對應傳遞新欄位
- [X] T245 [US3] 更新 `backend/src/api/checklists.py` 與 `backend/src/services/checklist_service.py`：（1）`GET /checklists/:id/cases` 的 ChecklistItemOut 新增 `test_data: list[TestDataOut]`（含四欄）與 `actual_values: dict[str, str]`；service 層聯查 TestData；（2）`PATCH /checklists/:id/cases/:case_id` request schema 新增 `actual_values: dict[str, str] | None`；service 序列化後寫入 `ChecklistItem.actual_values`

### 前端實作

- [X] T246 [US1] [US2] 更新 `frontend/src/pages/CaseDetailPage.vue` Tab 1「基本資訊」測試資料區塊：（1）**編輯模式**：改為四欄可編輯表格（易讀名稱、RF 變數（輸入易讀名稱後自動帶入 `${易讀名稱}`，可手動覆寫）、預設值、說明）；支援行內新增空白列（末尾插入）、行內直接編輯、刪除列；（2）**瀏覽模式**：四欄唯讀表格；表格欄對應後端欄位：易讀名稱←`field_name`、RF 變數←`rf_variable`、預設值←`field_value`、說明←`description`
- [X] T247 [US3] 更新 `frontend/src/pages/ChecklistDetailPage.vue`：每筆案例列新增展開/收合切換鈕（▶/▼，預設收合，多列可同時展開）；展開後顯示四欄測資表格（易讀名稱唯讀、RF 變數唯讀、預設值唯讀、實際值可編輯）；實際值欄位 onChange 後呼叫 `PATCH /checklists/:id/cases/:case_id` 傳入 `actual_values`；若案例無 test_data（陣列為空）展開後顯示「此案例無測試資料」
- [X] T248 [P] [US3] 更新 `frontend/src/services/checklistApi.ts`：ChecklistItemDetail 型別新增 `test_data: TestDataItem[]`（含 field_name/rf_variable/field_value/description 四欄）與 `actual_values: Record<string, string>`；新增或更新 `updateCaseItem(checklistId, caseId, payload: { notes?: string; actual_values?: Record<string, string> })` 對應 PATCH 端點

**Checkpoint**: `pytest backend/tests/contract/test_test_data_api.py backend/tests/contract/test_checklist_actual_values.py -v` 先 RED → 實作後 GREEN；`npm run dev` CaseDetailPage Tab 1 測試資料以四欄表格顯示；/checklists/:id 案例列可展開，填入實際值後 PATCH 持久化；下次開啟清單仍保留實際值

**Dependencies**: T239/T240（測試先 RED）→ T241（migration）→ T242/T243（model）→ T244/T245（API）→ T246/T247/T248（frontend）；T242/T243 可平行；T246/T247/T248 可平行

---

## Phase 26: 編輯模式自動從 RF 程式碼解析變數填入測資表格（FR-001 US1-15）（2026-07-04）

**Purpose**: 使用者進入案例編輯模式時，自動讀取已儲存的 RF 程式碼，解析所有非內建 `${VARIABLE_NAME}` 參照，以合併補齊策略填入測試資料表格（僅新增尚無的變數列，不覆蓋既有資料）。純前端變更，無後端修改、無 DB migration、無新 API endpoint。

### 實作（純前端）

- [X] T249 [US1] 更新 `automatic_test/frontend/src/pages/CaseDetailPage.vue` 的 `startEdit()` 函式：在初始化 `editTestData` 後，呼叫 `caseApi.getRobotScript(caseId)` 取得 RF 程式碼；以正規式 `/\$\{([^}]+)\}/g` 解析所有 `${VAR}` 參照，排除 RF_BUILTINS exclusion set（CURDIR/EXECDIR/TEMPDIR 等框架內建變數）；依 `rf_variable` 大小寫不分比對，僅將 `editTestData` 中尚無的變數以 `{ field_name: 名稱, rf_variable: '${名稱}', field_value: '', description: '', _rf_auto: false }` 格式新增為列；`getRobotScript` 回傳 404（尚無 RF 程式碼）時靜默略過，不中斷 `startEdit()` 流程

**Checkpoint**: 進入編輯模式後，`editTestData` 包含 RF 程式碼中所有非內建 `${VAR}` 的列（已存在者不重複）；已手動填入的列（field_value、description）不被覆蓋；無 RF 程式碼時 `editTestData` 維持原有狀態

**Dependencies**: 依賴 Phase 25（T246）完成，`editTestData` 四欄結構須已就緒；使用 Phase 18（T159/T162）建立的 `caseApi.getRobotScript` 既有 API

---

## Phase 27: Tab 2 立即試跑與 Chat 整合（FR-016 US1-16）（2026-07-04）

**Purpose**: 在 Tab 2「測試步驟」編輯介面中，測試人員可按「立即試跑」按鈕直接使用右側 RF 程式碼預覽區的當前內容執行試跑（無需先儲存案例）。試跑完成後自動將結果（pass/fail badge、執行時間、失敗訊息、截圖）以對話訊息形式附加至左側 Chat，並自動觸發 AI 分析失敗原因（若失敗）。核心修改：ChatMessage 新增 `type` 欄位（區分 `chat` vs `trial_run_result`），試跑 API 擴充，ExecutionService 新增試跑流程，前端 Chat 訊息渲染擴充。

### 合約測試（RED）

- [ ] T250 在 `backend/tests/contract/test_trial_run_api.py` 新增 POST `/cases/{case_id}/trial-run` 合約測試，request body 包含 `rf_code` 與 `case_name`（選填），驗證回傳 202 Accepted 與 `execution_id`；後續 `GET /cases/{id}/chat-history` 應包含 `type` 欄位

### 資料庫遷移

- [ ] T251 執行 `alembic revision --autogenerate -m "add_chat_message_type_field"` 並驗證 upgrade/downgrade：`case_chat_messages` 表新增 `type VARCHAR(30) NOT NULL DEFAULT 'chat'` 欄位，舊資料補全為 `'chat'`；檢查 model 的 Enum 型別相容

### 後端 Model 更新

- [ ] T252 [P] 更新 `backend/src/models/chat_message.py`：新增 `type = Column(Enum(ChatMessageType), nullable=False, default=ChatMessageType.CHAT)` 欄位，定義 `ChatMessageType` enum（`CHAT` / `TRIAL_RUN_RESULT`）；schema 中 ChatMessageOut 新增 `type` 欄位

### 後端 Service 與 API 實作

- [ ] T253 擴充 `backend/src/services/execution_service.py`：新增 `execute_trial_run_from_code(case_id: str, rf_code: str, case_name: str) -> ExecutionRecord` 方法；調用 RF 執行引擎，解析 output.xml，生成試跑結果訊息（status、elapsed_ms、error_message、screenshot_paths）；將結果寫入 case_chat_messages（`type=TRIAL_RUN_RESULT`）；若失敗則調用 `_generate_trial_run_analysis_prompt()` 組裝 prompt，調用 AI 分析，將 AI 回應寫入新的 ChatMessage（`type=CHAT`，`role=assistant`）
- [ ] T254 [P] 新增 `backend/src/services/ai_service.py` 方法 `analyze_trial_run_failure(case_name: str, error_message: str, rf_code: str, elapsed_ms: int) -> str`：組裝 prompt 包含失敗訊息與當前 RF 代碼，調用 LLM 分析並回傳建議修正的 RF 程式碼或步驟
- [ ] T255 [P] 擴充 `backend/src/api/cases.py`：POST `/cases/{case_id}/trial-run` endpoint 接受 request body `{ "rf_code": string, "case_name": string | null }`，調用 execution_service 試跑方法，回傳 202 Accepted 與 `{ execution_id, stream_url }`

### 前端實作

- [ ] T256 [P] 更新 `frontend/src/pages/CaseDetailPage.vue` Tab 2「測試步驟」右側 RF 程式碼預覽區：新增紫色「立即試跑」按鈕；若 RF 程式碼為空則按鈕禁用（disabled），懸停顯示提示「RF 程式碼為空，請先透過 Chat 生成程式碼」（SR-017）；點擊後呼叫 `POST /cases/{id}/trial-run` 傳入右側當前 RF 代碼文字（從 `RFCodePreview` 元件取值）與案例名稱；顯示 loading indicator 直至試跑完成；頁面應記錄試跑開始時間並於完成後驗證耗時 ≤60 秒（SC-011）
- [ ] T257 [P] 更新 `frontend/src/pages/CaseDetailPage.vue` Tab 2 左側 Chat 區域的訊息渲染邏輯（`ChatBubble` 元件）：支援 `type='trial_run_result'` 訊息型別；若 status='passed'，顯示綠色 PASS badge 與執行時間；若 status='failed'，顯示紅色 FAIL badge、執行時間、錯誤訊息、截圖縮圖廊道（可點擊放大）；其他 status（timeout/error）同樣顯示對應 badge

### 前端 API 更新

- [ ] T258 更新 `frontend/src/services/caseApi.ts`：ChatMessageModel 型別新增 `type: 'chat' | 'trial_run_result'` 欄位；若 `type='trial_run_result'`，content 為 JSON 物件，parseable 為 `{ status, elapsed_ms, error_message, screenshot_paths }`；`getChatHistory` 回應包含 `type` 欄位；新增或更新 `runTrialFromCode(caseId: string, rfCode: string, caseName?: string) -> Promise<{ execution_id: string; stream_url: string }>` 方法

### 端端與性能測試

- [ ] T259 [P] 在 `frontend/tests/e2e/trial-run.spec.ts` 新增 e2e 測試：（1）開啟案例編輯頁面進入 Tab 2；（2）輸入簡單 RF 代碼於右側預覽區或由 AI Chat 生成；（3）驗證「立即試跑」按鈕啟用；（4）清空 RF 代碼區，驗證「立即試跑」按鈕禁用且提示『RF 程式碼為空，請先透過 Chat 生成程式碼』；（5）恢復 RF 代碼，點擊「立即試跑」按鈕；（6）驗證試跑結果訊息出現在左側 Chat 區域；（7）若試跑失敗，驗證 AI 建議訊息隨後出現；（8）刷新頁面後驗證訊息持久化至對話歷史
- [ ] T260 在 `backend/tests/performance/test_trial_run_performance.py` 新增性能測試：建立簡單 RF 代碼案例，觸發試跑，驗證從請求送出到客戶端收到完整結果（含 Chat 訊息）的耗時 ≤60 秒（SC-011）；記錄實際耗時並留下效能基準線供未來優化

**Checkpoint**: `pytest backend/tests/contract/test_trial_run_api.py -v` 先 RED → 實作後 GREEN；`npm run dev` 進入 CaseDetailPage Tab 2，RF 代碼為空時「立即試跑」按鈕禁用；輸入 RF 代碼後按鈕啟用；點擊後看到試跑結果訊息出現在 Chat；試跑失敗時看到 AI 分析建議；頁面刷新後訊息仍存在；`pytest backend/tests/performance/test_trial_run_performance.py -v` 驗證 60 秒 SLA

**Dependencies**: T252（model）必須先完成才能執行 T253/T254；T253 與 T254 可平行；T256/T257/T258 可平行，均依賴 T252/T253/T254 完成；T259（e2e）與 T260（性能）依賴前端後端實作完成

---

## Notes

- `[P]` = 不同檔案，無未完成依賴，可平行執行
- `[Story]` 標籤對應 spec.md 中的 User Story
- TDD 順序嚴格：先寫測試確認 RED，再實作直到 GREEN，再 Refactor
- 每個測試任務必須在對應實作任務開始前存在且失敗
- 每完成一個 Phase 的 Checkpoint 後 commit
- 避免：模糊描述、相同檔案衝突、跨 Story 的破壞性依賴
