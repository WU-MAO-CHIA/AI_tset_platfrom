---
description: "Task list for RF Code Upload and AI Integration"
---

# Tasks: RF Code Upload and AI Integration

**Input**: Design documents from `/specs/002-rf-code-upload-ai/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/
**Tests**: Only include tests if explicitly requested in feature specification. Constitution mandates TDD (NON-NEGOTIABLE) so test tasks included where existing test patterns apply.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Web application (Option 2):
- Backend: `backend/src/`
- Frontend: `frontend/src/`
- Tests: `backend/tests/`, `frontend/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project dependencies and shared utilities

- [x] T001 [P] Add `monaco-editor` and `@monaco-editor/loader` to `frontend/package.json` for Robot Framework syntax highlighting
- [x] T002 Create `frontend/src/utils/rfUpload.ts` with shared validation constants (`MAX_FILE_SIZE = 500 * 1024`, `.robot` extension check, encoding fallback: utf-8-sig/big5/gbk)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core API endpoint and client method that both US1 and US3 depend on

- [x] T003 [P] Add `POST /cases/{case_id}/robot-script/upload` endpoint in `backend/src/api/cases.py` with server-side validation (extension `.robot`, size ≤ 500KB, UTF-8 decode with fallback), persists via `RobotScriptRepository.upsert` + sync to `settings.robot_scripts_dir`
- [x] T004 [P] Add `uploadRobotScript(caseId, file)` method in `frontend/src/services/caseApi.ts` calling the new endpoint

---

## Phase 3: User Story 1 - Upload RF Code in Test Case Creation (Priority: P1) 🎯

**Goal**: Allow users to upload a .robot file during test case creation, preview it, and save with the case

**Independent Test**: Create a test case with uploaded .robot file; verify it's stored, retrievable via `GET /robot-script`, and visible in case detail

### Tests for User Story 1 (Constitution III: Test-First)

> Write these tests FIRST, ensure they FAIL before implementation

- [x] T005 [P] [US1] Contract test: Add upload endpoint tests in `backend/tests/contract/test_cases_api.py` (success, non-.robot 400, >500KB 413, encoding error 400)
- [x] T006 [P] [US1] Unit test: Add case creation + RF persistence test in `backend/tests/unit/test_case_service.py`

### Implementation for User Story 1

- [x] T007 [US1] Create `frontend/src/components/RFCodeUpload/index.vue` with file picker (accept=".robot"), client-side validation using `rfUpload.ts`, emits `file-loaded` with decoded content
- [x] T008 [US1] Integrate `RFCodeUpload` + `RFCodePreview` into `frontend/src/components/TestCaseForm/index.vue`: on create, buffer file content; after case creation call `uploadRobotScript(caseId, bufferedFile)`; display returned RF code in preview
- [x] T009 [US1] Create `frontend/tests/unit/RFCodeUpload.spec.ts` with validation and upload flow tests
- [x] T010 [US1] Extend `frontend/tests/unit/TestCaseForm.spec.ts` with create→upload→save integration tests

**Checkpoint**: Creating a test case with .robot upload stores code in DB + disk, preview shows content, retrievable via API

---

## Phase 4: User Story 2 - AI Reads Uploaded RF Code in Chat (Priority: P1)

**Goal**: AI chat includes uploaded RF code as context with user-controllable scope (full/summary/none)

**Independent Test**: Upload RF code to a case, open AI chat, ask about the code; verify AI response references uploaded code; switch context mode and verify behavior

### Tests for User Story 2

- [x] T011 [P] [US2] Unit test: Add `chat_and_generate_rf` context injection tests in `backend/tests/unit/test_ai_service.py` (full/summary/none modes, no RF code backward compatibility)

### Implementation for User Story 2

- [x] T012 [US2] Extend `AIService.chat_and_generate_rf` in `backend/src/services/ai_service.py`: add `rf_code: Optional[str]`, `rf_context_mode: Literal["full","summary","none"]`; inject `---UPLOADED RF CODE---` block into system prompt for full mode; generate summary for summary mode; skip for none/empty
- [x] T013 [US2] In `backend/src/api/cases.py`: add `rf_context_mode` to `ChatRequest`; in `chat_with_ai` fetch RobotScript via repo and pass to `ai_service.chat_and_generate_rf`
- [x] T014 [US2] Add `rf_context_mode` parameter to `chatWithAI` in `frontend/src/services/caseApi.ts`
- [x] T015 [US2] Add context mode selector (完整/摘要/無) and RF context indicator in `frontend/src/components/AIChatPanel/index.vue`, pass mode to `chatWithAI`
- [x] T016 [US2] Extend `frontend/tests/unit/AIChatPanel.spec.ts` with context mode selector and payload tests

**Checkpoint**: AI chat correctly references uploaded RF code; context mode selector works; backward compatible with cases without RF code

---

## Phase 5: User Story 3 - Preview and Edit Uploaded RF Code (Priority: P2)

**Goal**: Syntax-highlighted Monaco editor for RF code preview/editing; save edited version; clear removes RF code

**Independent Test**: Upload RF code, view in editor with syntax highlighting, edit, save; verify edited version stored; clear editor and save; verify RF code removed from DB + disk

### Implementation for User Story 3

- [x] T017 [P] [US3] Create `frontend/src/components/RFCodeEditor/index.vue`: Monaco wrapper, register `robotframework` language (Monarch tokens for keywords/strings/comments, bracket/comment config), v-model binding for content
- [x] T018 [US3] Use `RFCodeEditor` in `frontend/src/pages/CaseDetailPage.vue` edit flow (and `TestCaseForm` for create flow) to display existing RF code with syntax highlighting and allow editing
- [x] T019 [US3] After edit, save via existing `PUT /cases/{case_id}/robot-script` (reuses `saveRobotScript` in `caseApi.ts`)
- [x] T020 [US3] Extend `PUT /{case_id}/robot-script` in `backend/src/api/cases.py`: if `rf_code` is empty string, delete RobotScript record + remove disk file (`settings.robot_scripts_dir/{case_number}.robot`)
- [x] T021 [US3] Create `frontend/tests/unit/RFCodeEditor.spec.ts` for Monaco initialization, language registration, content binding
- [x] T022 [US3] Update `frontend/tests/unit/RFCodePreview.spec.ts` for editor-based edit flow

**Checkpoint**: RF code shows syntax-highlighted in editor; edits persist; clearing removes DB record and disk file

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Full validation, compatibility, and quality gates

- [ ] T023 Run backend test suite: `pytest backend/tests -q`
- [ ] T024 Run frontend unit tests: `cd frontend && npm test`
- [ ] T025 [P] Execute `quickstart.md` validation scenarios: upload valid .robot → create case → verify; upload invalid → verify rejection; AI chat with context modes; clear RF code → verify removal
- [ ] T026 Verify backward compatibility: cases without RF code work unchanged in chat and trial run
- [ ] T027 Run lint/typecheck: `cd backend && python -m ruff check` (if configured) / `cd frontend && npm run lint`

---

## Phase 7: 建立頁無狀態對話（截圖錯誤修復）

**Purpose**: 修復「建立測試案例 → 測試步驟」頁籤 AI 對話失敗（`AIChatPanel` 無 `caseId`，`POST /cases//chat` 註定 404，前端只顯示通用錯誤）

- [x] T028 [P] 後端 `backend/src/api/cases.py` 新增 `ChatPreviewRequest` + `POST /cases/chat-preview`（無狀態：不查案例、不寫 DB，接受 `history`/`rf_code`）
- [x] T029 [P] 前端 `frontend/src/services/caseApi.ts` 新增 `ChatPreviewRequest` 型別 + `chatPreview()` 方法
- [x] T030 `frontend/src/components/AIChatPanel/index.vue`：無 `caseId` 時改走 `chatPreview`（本地 history），`catch` 顯示後端真實訊息
- [x] T031 [P] 測試：`backend/tests/contract/test_cases_api.py` 新增 `TestChatPreviewEndpoints`；`frontend/tests/unit/AIChatPanel.spec.ts` 新增無 `caseId` + 錯誤訊息測試；`contracts/api.md` 新增 §4b

---

## Phase 8: 儲存案例 500 修復（建立頁 `An unexpected error occurred`）

**Purpose**: `case_number_sequences` 為空但 `test_cases` 已有 `MMA-001`，`get_next_case_number("MMA")` 回傳重複編號 → UNIQUE 違規 → 500

- [x] T032 [P] `backend/src/repositories/test_case_repo.py`：`get_next_case_number` 首次使用某 prefix 時以既有最大後綴播種（非數字後綴略過）
- [x] T033 `backend/src/api/cases.py`：`create_case` 捕捉 `IntegrityError` 回 409 `case_number_conflict`（不再是無意義 500）
- [x] T034 [P] 測試：`backend/tests/unit/test_case_number_sequence.py`（真實 SQLite：播種/新 prefix/非數字後綴/完整寫入）；以真實 DB 複本驗證 MMA → MMA-002 → MMA-003

---

## Phase 9: 執行頁 error＋0/0＋SSE connection failed 修復

**Purpose**: 試跑後執行頁顯示 error、0/0、`SSE connection failed`

- [x] T035 `backend/src/api/executions.py`：stream 端點改用 `Cookie()` 讀取登入 cookie（名稱修正為 `access_token`；原本參數被綁成 query param 且名稱錯誤，導致一律 401）
- [x] T036 `backend/src/api/executions.py`：`finally` 內 `yield` 改為 flag 制（原本每次正常結束也會補發 `execution_error 執行逾時`，把成功的串流翻成 error）
- [x] T037 `backend/src/api/cases.py`：無 RF 程式碼試跑直接回 422 `no_robot_code`（不再建一筆即時失敗的紀錄）
- [x] T038 [P] 測試：`backend/tests/integration/test_sse_stream.py`（隔離記憶體 DB：無 token 401／cookie 200＋事件完整／無假性逾時錯誤／query token 相容／無碼試跑 422／不存在案例 404；已驗證修復前 cookie 測試確實 401 失敗）

---

## Phase 10: AI 探索網頁取得定位器（Page Explorer Agent）

**Purpose**: AI 駕駛無頭瀏覽器探索真實頁面（含登入），產出元素目錄（建議 locator＋相對 XPath＋CSS）並餵給 AI 對話

- [x] T039 [P] 依賴：`requirements.txt`＋venv 安裝 `playwright==1.49.1`，`playwright install chromium`（headless shell，驗證可啟動）
- [x] T040 [P] `backend/src/services/page_explorer_service.py`：goto/snapshot/screenshot/click/fill/get_locators；JS 生成相對 XPath（id/testid 錨點＋唯一性驗證）與規範式 recommended；URL SSRF 守衛（限 http/https、擋內網）
- [x] T041 `backend/src/services/page_agent_service.py`：純文字 ReAct 迴圈（相容三家 provider）、憑證變數服務端解析＋全程遮罩、步數上限、finish 彙整 catalog
- [x] T042 `backend/src/services/explore_session_store.py`＋`cases.py`：`POST explore-page`（202＋editor 權限）背景執行、`GET explore-sessions/{id}` poll；記憶體 session＋TTL，無 migration
- [x] T043 AI 串接：`ChatRequest`/`ChatPreviewRequest`＋`catalog`，`ai_service` 注入 `KNOWN PAGE ELEMENTS` 段
- [x] T044 前端：`caseApi`（explore/catalog 型別＋方法）、`PageExplorer` 面板（啟動/poll/目錄表/複製/帶入對話）、`CaseDetailPage` 編輯模式「頁面探索」頁籤、`AIChatPanel` 透傳 catalog
- [x] T045 [P] 測試：`test_page_agent.py`（15，含遮罩外洩斷言）、`test_explore_api.py`（6，隔離 DB＋stub agent）、`PageExplorer.spec.ts`（4）、`AIChatPanel` catalog 透傳；真瀏覽器冒煙（snapshot/XPath 唯一性/click/fill＋agent 全鏈路）全過；`contracts/api.md` §7

---

## Phase 11: Code Review 指出的 11 項修復

**Purpose**: 修復 review 發現的 9 個 bug＋housekeeping（T046–T055）

- [x] T046 [P] #1 憑證變數大小寫：fill 查表統一 upper（`${username}` 亦可）；單元測試
- [x] T047 [P] #4 序號播種：seed INSERT 加 `ON CONFLICT DO NOTHING`；LIKE 跳脫 `%_굶`；萬用字元字首測試
- [x] T048 [P] #5 `max_steps=0` 回 422（`is not None`）；端點測試
- [x] T049 #6 試跑守衛改 DB 優先（`RobotScriptRepository`＋磁碟 fallback）；`_execute_trial_bg` 同步改為 body→DB→磁碟；DB 有碼無檔回 202 測試
- [x] T050 [P] #7 SSRF 檢查改 `asyncio.to_thread`；TOCTOU＋多 worker 限制寫入註解／docstring
- [x] T051 [P] #8 prompt 誠實化：`xpath_unique=false` 逐條標註注意＋表頭聲明修正
- [x] T052 #2 stateless history 去重（先取 history 再 push）；#3 `apiClient` 讀 `detail.message`（字串或物件皆處理）；訊息不重複＋rfCodeContext 透傳測試
- [x] T053 #9 rf_code 貫通：`TestCaseForm` 新增 `rf-buffered` 事件 → `CaseCreatePage` 持有 → `AIChatPanel.rfCodeContext` → `chatPreview.rf_code`；emit 測試
- [x] T054 #10 PageExplorer 改 setTimeout 鏈＋立即首查（不重疊）；既有 4 測試全過
- [x] T055 [P] #11 housekeeping：多 worker 限制寫入 `explore_session_store` docstring（`.env.example` 被刪為既有狀態，未動；SSE CORS 需 staging 驗證，已註記）

---

## Phase 12: 結果頁 iframe 渲染 404 JSON 修復

**Purpose**: 執行結果頁在無 RF 報告時把 `{"detail":"報告尚未生成或不存在"}` 直接顯示在報告區，且失敗原因無處可看（006eba44：checklist 執行遇到無碼案例 → skipped → failed，無報告檔）

- [x] T056 `execution_service.py`：無碼訊息中文化（`尚無 RF 程式碼（請先透過 AI 對話生成或上傳）`）
- [x] T057 `executions.py`：新增 `GET /{id}/rf-report-status`（供 UI 預檢，避免 iframe 渲染 404 JSON）
- [x] T058 前端 `ResultPage.vue`：終態先預檢報告（有才掛 iframe，否則中文 placeholder＋首個失敗原因）；新增案例結果表（編號／名稱／狀態／耗時／失敗訊息，skipped 中文化）
- [x] T059 [P] 測試：`TestRfReportStatus`（無檔案 false／有檔案 true／不存在 404）；`ResultPage.spec.ts`（結果表＋失敗訊息／缺報告 placeholder 且無 iframe／有報告掛 iframe）

---

## Phase 13: 建立頁 RF 程式碼遺失修復（MMA-002 儲存無效）

**Purpose**: 建立頁 Tab2 AI 生成的 RF 碼在儲存案例後被無聲丟棄（`CaseCreatePage.onSaved` 直接導頁）；且表單上傳區在已有程式碼時永遠隱藏、無法覆寫（FR-012）

- [x] T060 `TestCaseForm`：上傳控制永遠顯示＋有內容即預覽（可覆寫）；建立分支不再自行上傳（避免與父層重複／遺漏）；新增 `takePendingRfCode()`＋`defineExpose`
- [x] T061 `CaseCreatePage.onSaved`：導頁前先持久化 RF（Tab1 上傳檔優先，其次 Tab2 AI 碼；無碼直接導頁；失敗留頁顯示錯誤重試）
- [x] T062 [P] 測試：`CaseCreatePage.spec.ts`（AI 碼儲存後導頁／上傳優先／無碼直導／失敗留頁）；`TestCaseForm` 修正 3 個過時斷言＋新增 `takePendingRfCode`；全相關套件 6 檔 49/49 全綠（含順手修好的 2 個 case_number 陳舊測試）

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — blocks US1/US3 upload integration
- **US1 (Phase 3)**: Depends on Foundational (T003, T004) — T005/T006 (tests) before T007-T010
- **US2 (Phase 4)**: Depends on Foundational (uses existing RobotScript repo) — T011 (test) before T012-T016
- **US3 (Phase 5)**: Depends on Foundational + US1 (upload provides content) — T017-T022
- **Polish (Phase 6)**: Depends on all desired user stories complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependency on other stories
- **US2 (P1)**: Can start after Foundational — independent of US1/US3 (reads existing RobotScript)
- **US3 (P2)**: Can start after Foundational — benefits from US1 upload but can use AI-generated code too

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Constitution III)
- Models/repositories before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T001, T002 (Setup) — different files, parallel
- T003, T004 (Foundational) — different files (backend vs frontend), parallel
- T005, T006 (US1 tests) — different test files, parallel
- T011 (US2 test) can run parallel to US1 implementation
- T017 (US3 editor) can start once Setup complete
- All Phase 6 tasks T023-T027 can run in any order after stories complete

### Parallel Example: US1

```bash
# Launch contract + unit tests together:
Task: "Contract test for upload endpoint in backend/tests/contract/test_cases_api.py"
Task: "Unit test for case creation + RF persistence in backend/tests/unit/test_case_service.py"

# Launch frontend component tests together:
Task: "RFCodeUpload unit tests in frontend/tests/unit/RFCodeUpload.spec.ts"
Task: "TestCaseForm integration tests in frontend/tests/unit/TestCaseForm.spec.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — upload endpoint blocks US1 frontend)
3. Complete Phase 3: User Story 1 (tests first → backend → frontend)
4. **STOP and VALIDATE**: Test US1 independently — create case with .robot upload → verify stored → verify retrievable
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test independently → Deploy/Demo (MVP!)
3. Add US2 → Test independently → Deploy/Demo
4. Add US3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (upload flow)
   - Developer B: US2 (AI context)
   - Developer C: US3 (Monaco editor)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD mandated by Constitution III)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence