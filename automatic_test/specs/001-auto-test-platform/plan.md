# Implementation Plan: 自動化測試平台 (Automatic Test Platform)

**Branch**: `001-auto-test-platform` | **Date**: 2026-07-04 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-auto-test-platform/spec.md`

## Summary

全端自動化測試管理平台，支援測試案例 CRUD（含 AI 步驟補齊、多媒體上傳、版本管理）、測試清單管理、Robot Framework + pabot 平行執行、SSE 即時進度推送、RF 原生報告嵌入，以及登入驗證（JWT）與管理後台（帳號 / 系統別 / LLM API Key 管理）。

技術方向：Python 3.11 FastAPI 後端 + Vue 3 TypeScript 前端 + SQLAlchemy async + Alembic migrations。所有主要架構決策已記錄於 research.md（Decision 1–12）。

## Technical Context

**Language/Version**: Python 3.11+ (backend)、Node.js 18+ / TypeScript 5 (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 async, Alembic, pabot, robotframework-browser, Anthropic SDK, OpenAI SDK, python-jose[cryptography], passlib[bcrypt], Vue 3, Pinia, Vue Router 4, Axios  
**Storage**: SQLite（開發 / 初期部署），本地檔案系統（媒體附件、RF 執行報告、robot scripts）  
**Testing**: pytest + pytest-asyncio (backend)、Vitest (frontend)  
**Target Platform**: Linux server (headless Chromium)  
**Project Type**: Web application（FastAPI REST API + Vue 3 SPA）  
**Performance Goals**: 篩選 ≤2s（千筆）、SSE 推送延遲 ≤2s、AI 補齊 ≤15s、RF 代碼生成 ≤35s  
**Constraints**: 單機部署、pabot 並行數預設 5、媒體圖片 ≤10MB / 影片 ≤100MB  
**Scale/Scope**: 10 名測試人員同時操作，千筆案例規模

## Constitution Check

| Gate | 狀態 | 說明 |
|------|------|------|
| III. Test-First | ✅ | Phase 25：T239/T240 contract tests 先寫（RED），migration/model/API/前端後實作 |
| VI. Python 3.11+ | ✅ | 後端維持 Python 3.11+ |
| VI. Service/Repository | ✅ | 新欄位擴充既有 CaseService / ChecklistService，符合分層設計 |
| VI. TypeScript + Vue | ✅ | 前端採 Vue 3 + TypeScript |
| V. Simplicity (YAGNI) | ✅ | Phase 25 僅新增最小欄位，無新 entity 或新 service |
| Security (FR-027) | ✅ | LLM 金鑰維持 `.env` 唯讀，`actual_values` 非機密資料 |

## Project Structure

### Documentation (this feature)

```text
specs/001-auto-test-platform/
├── plan.md              # This file
├── research.md          # Architecture decisions (Decision 1–12)
├── data-model.md        # Entity definitions（含 Phase 25 新欄位）
├── quickstart.md        # Integration scenarios
├── contracts/           # API contracts（含 Phase 25 更新）
└── tasks.md             # Task breakdown（Phase 1–25）
```

### Source Code

```text
automatic_test/
├── backend/
│   ├── src/
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── repositories/    # Data access layer
│   │   ├── services/        # Business logic
│   │   ├── api/             # FastAPI routers
│   │   ├── core/            # config, database, security, dependencies
│   │   └── execution/       # RF listener plugin
│   ├── alembic/             # DB migrations
│   ├── robot_scripts/       # Generated .robot files + results
│   └── data/                # execution_reports/{execution_id}/
└── frontend/
    └── src/
        ├── components/      # Reusable Vue components
        ├── pages/           # Route-level pages
        ├── services/        # API clients (Axios)
        ├── stores/          # Pinia stores
        └── router/          # Vue Router + navigation guards
```

## Key Research Decisions

| # | 決策 | 詳見 |
|---|------|------|
| 1 | LLM 多模型：Provider 抽象層（Anthropic + OpenAI） | research.md |
| 2 | RF 整合：pabot + RF Listener Plugin + XML 解析 + RF Browser | research.md |
| 3 | 媒體儲存：本地檔案系統，路徑設定化 | research.md |
| 4 | 平行執行：pabot `--processes N`，N 由 `PARALLEL_MAX_WORKERS` 控制 | research.md |
| 5 | 即時進度：SSE + RF Listener Plugin（asyncio.Queue） | research.md |
| 6 | Excel/CSV：openpyxl + csv，標頭比對 + 預覽確認 | research.md |
| 7 | 案例編號：system_category 前綴 + 三位數序號，查最大值+1 | research.md |
| 8 | RF script 儲存：實體檔案 `robot_scripts/{case_number}.robot` | research.md |
| 9 | SSE session 隔離：每輪輪詢新 AsyncSessionLocal，避免 SQLite snapshot | research.md |
| 10 | 背景任務 session：@staticmethod + 自建 session，禁用 request-scoped | research.md |
| 11 | RF 報告持久化：shutil.copytree → data/execution_reports/{id}/ | research.md |
| 12 | Auth / Admin：JWT Token + passlib bcrypt + 三角色 RBAC | research.md |
| 13 | RF 變數解析：前端正規式 + RF_BUILTINS exclusion set，合併補齊策略 | research.md |

## Implementation Progress

### 已完成 Phase 1–24

| Phase | 內容 | 狀態 |
|-------|------|------|
| 1 | 專案初始化（目錄結構、設定檔） | ✅ |
| 2 | 基礎架構（database, config, router, apiClient） | ✅ |
| 3 | US1 建立測試案例（CRUD, AI 補齊, 媒體上傳, 試跑） | ✅ |
| 4 | US2 瀏覽與篩選（篩選, 詳情 Tab, Excel/CSV 匯入, 執行歷史） | ✅ |
| 5 | US3 測試清單管理（CRUD, 案例挑選） | ✅ |
| 6 | US4 串接資料庫（DB 連線管理, 查詢撈取） | ✅ |
| 7 | US5 執行測試（RF 執行, SSE 進度, 報告產生） | ✅ |
| 8 | RF 代碼生成（Tab 2 Chat, 儲存, 執行時使用） | ✅ |
| 9 | 試跑（Trial Run）結果頁 | ✅ |
| 10 | 媒體附件（上傳, AI 上下文） | ✅ |
| 11 | Excel/CSV 匯入（預覽, 追加/取代） | ✅ |
| 12 | 平行執行（pabot, ExecutionListener, output.xml） | ✅ |
| 13 | RF 報告嵌入（log.html / report.html iframe） | ✅ |
| 14 | 全域導覽列（漢堡選單 < 768px, Noto Sans TC） | ✅ |
| 15 | 測試清單 CRUD（編輯/刪除, 案例管理畫面） | ✅ |
| 16 | 案例清單排序（case_number/name/system_category/created_at, server-side） | ✅ |
| 17 | 試跑防重複, 系統重啟結果頁清理 | ✅ |
| 18 | RF script 持久化（PUT /robot-script, GET /robot-script, 頁面自動載入） | ✅ |
| 19 | version 欄排序 + checklists 列表排序 + 操作按鈕樣式 | ✅ |
| 20 | 登入畫面 + JWT 驗證 + 三角色 RBAC + 管理後台 | ✅ |
| 21 | RF Remote 混合執行（⏸ 暫緩） | ⏸ |
| 22 | 執行前空清單驗證（FR-009 pre-flight） | ✅ |
| 23 | LLM 設定 env-only + 後台唯讀遮罩（FR-027） | ✅ |
| 24 | 本地 Ollama 整合 + 後台「目前啟用模型」可切換（FR-012/027） | ✅ |
| 25 | 測資變數四欄表格 + 清單案例展開列（FR-001/005/006/023） | ✅ |
| 26 | 編輯模式自動從 RF 程式碼解析變數填入測資表格（FR-001 US1-15） | ✅ 完成 |
| 27 | Tab 2 立即試跑與 Chat 整合（FR-016 US1-16） | 🔄 規劃中 |

---

## Phase 25：測資變數四欄表格 + 清單案例展開列（FR-001 / FR-005 / FR-006 / FR-023）

### 背景

本 Phase 源自 2026-07-04 兩輪 `/speckit-clarify` 釐清：

1. **測資變數四欄表格**（FR-001/FR-005）：TestData 現有 2 欄（field_name、field_value）需擴充至 4 欄（易讀名稱、RF 變數、預設值、說明），CaseDetailPage Tab 1 需顯示 4 欄表格，編輯模式支援行內新增/編輯/刪除，RF 變數預設自動帶入 `${易讀名稱}`。
2. **清單案例展開列**（FR-006/FR-023）：ChecklistDetailPage 的案例列需支援展開/收合，展開後顯示 4 欄測資表格（易讀名稱唯讀、RF 變數唯讀、預設值唯讀、實際值可編輯），實際值持久化至 ChecklistItem。

### 資料模型變更

**TestData（新增欄位）**:

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| rf_variable | VARCHAR(200) | nullable | RF 變數名稱（如 `${username}`）；空時前端自動顯示 `${field_name}` |
| description | TEXT | nullable | 說明 / 備註 |

**ChecklistItem（新增欄位）**:

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| actual_values | TEXT | nullable | JSON 字串，格式 `{rf_variable: actual_value, ...}`；執行時優先於案例預設值 |

### 後端修改範圍

| 檔案 | 變更 |
|------|------|
| `alembic/versions/xxx_phase25_test_data_checklist_item.py` | migration：`test_data` 加 `rf_variable`, `description`；`checklist_items` 加 `actual_values` |
| `src/models/test_data.py` | 新增 `rf_variable: str` (nullable)、`description: str` (nullable) |
| `src/models/checklist_item.py` | 新增 `actual_values: str` (nullable, JSON text) |
| `src/api/cases.py` | `TestDataSchema` 加入 `rf_variable`、`description`；create/update 處理自動帶入 rf_variable 邏輯 |
| `src/api/checklists.py` | `GET /checklists/:id/cases` 回傳每個 case 的 `test_data` 陣列；`PATCH /checklists/:id/cases/:case_id` 接受 `actual_values` JSON |
| `src/services/checklist_service.py` | `update_checklist_item_actual_values()` 方法 |

**rf_variable 自動帶入規則**（後端）：
- 前端送出 `rf_variable` 為空字串或 `null` 時，後端**不自動填入**（由前端負責顯示 fallback）
- 前端儲存時若 `rf_variable` 未手動覆寫，送出 `${field_name}` 作為值

### 前端修改範圍

| 檔案 | 變更 |
|------|------|
| `src/pages/CaseDetailPage.vue` | Tab 1：測試資料改為 4 欄表格；編輯模式支援行內新增/編輯/刪除；RF 變數欄位輸入時自動帶入 `${易讀名稱}` 作為預設值 |
| `src/pages/ChecklistDetailPage.vue` | 案例列加入 ▶/▼ 展開鈕（預設收合）；展開區域顯示 4 欄測資表格；實際值欄可編輯，失焦後呼叫 PATCH API |
| `src/services/checklistApi.ts` | 新增 `ChecklistCaseItem` type（含 `test_data`）；新增 `updateCaseActualValues(checklistId, caseId, actualValues)` |

### TDD 執行順序

```
T239（合約測試 RED：4 欄 TestData API）
T240（合約測試 RED：ChecklistItem actual_values API）
  ↓
T241（Alembic migration）
  ↓
T242（TestData model）  ← 可平行
T243（ChecklistItem model）
  ↓
T244（cases.py API）    ← 可平行
T245（checklists.py + checklist_service.py）
  ↓
T246（CaseDetailPage.vue）   ← 可平行
T247（ChecklistDetailPage.vue）
T248（checklistApi.ts）
```

### 驗收條件

- `GET /api/v1/cases/:id` 回傳 `test_data[].rf_variable` 與 `test_data[].description` 欄位。
- `POST/PUT /api/v1/cases` 接受 `test_data[].rf_variable` 與 `test_data[].description`。
- `GET /api/v1/checklists/:id/cases` 回傳每個 case item 的 `test_data` 陣列（4 欄）。
- `PATCH /api/v1/checklists/:id/cases/:case_id` 接受 `actual_values` JSON 並持久化。
- CaseDetailPage Tab 1 顯示 4 欄表格；編輯模式可新增/編輯/刪除列；RF 變數自動帶入 `${易讀名稱}`。
- ChecklistDetailPage 案例列預設收合；點擊展開顯示 4 欄表格；實際值可編輯並持久化。

---

## Phase 26：編輯模式自動從 RF 程式碼解析變數填入測資表格（FR-001 US1-15）

### 背景

源自 2026-07-04 `/speckit-clarify` 釐清：使用者進入案例編輯模式時，系統應自動讀取該案例已儲存的 RF 程式碼，解析所有非內建的 `${VARIABLE_NAME}` 參照，以合併補齊策略填入測試資料表格，減少手動輸入工作量。

### 範圍

**純前端變更**，無後端修改、無資料庫遷移、無新 API endpoint。

使用既有 `caseApi.getRobotScript(caseId)` → `GET /cases/:id/robot-script`（Phase 18 已實作）。

### 前端修改範圍

| 檔案 | 變更 |
|------|------|
| `src/pages/CaseDetailPage.vue` | `startEdit()` 增加 RF 變數解析邏輯：呼叫 `getRobotScript`，解析 `${VAR}` 並合併補齊 `editTestData` |

### 實作細節

**RF 內建變數排除清單**（`RF_BUILTINS`）：
```typescript
const RF_BUILTINS = new Set([
  'CURDIR', 'EXECDIR', 'TEMPDIR', 'OUTPUT_DIR', 'OUTPUT_FILE',
  'LOG_FILE', 'REPORT_FILE', 'DEBUG_FILE', 'SUITE_NAME', 'SUITE_SOURCE',
  'SUITE_DOCUMENTATION', 'SUITE_STATUS', 'SUITE_MESSAGE', 'TEST_NAME',
  'TEST_DOCUMENTATION', 'TEST_STATUS', 'TEST_MESSAGE', 'PREV_TEST_NAME',
  'PREV_TEST_STATUS', 'PREV_TEST_MESSAGE', 'LOG_LEVEL',
  'True', 'False', 'None', 'null', 'EMPTY', 'SPACE',
])
```

**合併邏輯**：
- 比對鍵：`rf_variable`（大小寫不分，如 `${USERNAME}` 與 `${username}` 視為相同）
- 新增列的 `field_name` = 提取名稱（去除 `${}`，保留原始大小寫）
- `rf_variable` = `${原始名稱}`、`field_value` = `''`、`description` = `''`、`_rf_auto` = `false`
- 若 `getRobotScript` 回傳 404（尚無 RF 程式碼），靜默略過，不中斷 `startEdit()` 流程

### TDD 執行順序

```
T249（CaseDetailPage.vue：startEdit() 加入 RF 變數解析 + 合併邏輯）
```

### 驗收條件

- 進入編輯模式後，`editTestData` 包含 RF 程式碼中所有非內建 `${VAR}` 的列（已存在者不重複）。
- 已手動填入的列（`field_value`、`description`）不被覆蓋。
- 無 RF 程式碼時，`editTestData` 維持原有狀態。

---

## 待實作功能

### Phase 21：RF Remote 混合執行模式 ⏸ 暫緩

> **狀態**：設計完成，暫緩實作，待需求確認後再排入 tasks.md。

**背景**：Windows GUI 測試案例無法在 Linux Server 本地執行，需透過 RF Remote Library 將 Keyword 路由至 Windows Remote Server 執行；非 GUI 案例維持現有本地執行邏輯。

**目標**：
1. 測試案例可指定執行模式（`local` / `remote`）
2. 遠端執行時自動在 `.robot` 頭部插入 `Library  Remote  {url}`
3. Remote Server URL 統一在管理後台設定
4. 同一清單中可混合本地與遠端案例，各自獨立執行

**後端修改範圍**：

| 項目 | 說明 |
|------|------|
| `TestCase` model | 新增 `execution_mode: str`（預設 `'local'`） |
| Alembic migration | `test_cases` 表加 `execution_mode` 欄位 |
| `AppSetting` | 新增 key `remote_server_url`（如 `http://192.168.1.10:8270`） |
| `ExecutionService` | 執行前讀取 `execution_mode`；若為 `remote`，在 script 頭部插入 `Library  Remote  {remote_server_url}` |
| `CaseService` / `cases.py` | create/update API 加入 `execution_mode` 欄位 |
| `app_setting_service.py` | 新增 `get_remote_server_url()` / `set_remote_server_url()` |
| `admin.py` | 新增 Remote Server URL 的 GET/PUT endpoint |

**前端修改範圍**：

| 項目 | 說明 |
|------|------|
| `TestCaseForm` | 新增「執行模式」切換（本地 / 遠端 Remote Server） |
| `TestCaseList` | 遠端案例顯示 `[R]` 標記 |
| `CaseDetailPage` | 唯讀顯示執行模式 |
| `AdminPage` | LLM Keys tab 旁新增「Remote Server」tab，設定 URL + 連線測試按鈕 |
| `adminApi.ts` | 新增 `getRemoteServerUrl()` / `setRemoteServerUrl()` |

---

## Phase 27：Tab 2 立即試跑與 Chat 整合（FR-016 US1-16）

### 背景

源自 2026-07-04 `/speckit-clarify` 澄清：在 Tab 2「測試步驟」編輯介面中，測試人員需快速驗證右側 RF 程式碼預覽區的當前內容是否可執行。按「立即試跑」按鈕應直接使用當前 RF 代碼執行試跑，完成後將結果（pass/fail badge、執行時間、失敗訊息、截圖）以對話訊息形式附加至左側 Chat，並自動觸發 AI 分析失敗原因（若失敗）。

### 範圍

**後端修改**:
- ChatMessage model 新增 `type` 欄位（`chat` / `trial_run_result`），Alembic migration 補全舊資料
- 新增或擴充試跑 API：`POST /cases/{case_id}/trial-run-from-code` 或改擴 `POST /cases/{case_id}/trial-run` 接受 `rf_code` 參數
- ExecutionService 新增試跑流程（讀取 RF code → 執行 → 解析結果 → 生成 trial_run_result 訊息 → 自動 AI 分析）
- AI 服務新增失敗分析 prompt 組裝函式（將試跑結果嵌入）

**前端修改**:
- CaseDetailPage Tab 2：右側 RF 程式碼預覽區新增「立即試跑」按鈕
- Chat 訊息渲染邏輯擴充：支援 `type='trial_run_result'` 訊息（badge + 執行時間 + 錯誤訊息 + 截圖廊道）
- chat-history API 回應格式新增 `type` 欄位

**資料庫修改**:
- Alembic migration：`case_chat_messages` 表新增 `type` 欄位（VARCHAR(30)），舊資料補全為 `'chat'`

### 資料流

```
測試人員進入 Tab 2 編輯模式
    ↓
右側 RF 程式碼預覽區按「立即試跑」按鈕
    ↓ (不需先儲存案例)
前端呼叫 POST /cases/{id}/trial-run，request body 含 RF 代碼文字
    ↓
後端建立 ExecutionRecord（`execution_type='trial_run'`），開啟背景任務
    ↓
背景任務執行 RF code → 解析 output.xml → 生成 trial_run_result 訊息
    ↓ (成功 / 失敗)
寫入 CaseChatMessage（`type='trial_run_result'`）
    ↓
若失敗，自動組裝 AI 分析 prompt，調用 AI 服務
    ↓
AI 回應作為新 ChatMessage（`type='chat'`）附加
    ↓
前端 SSE 推送兩條訊息 → 左側 Chat 區更新顯示
```

### TDD 執行順序

```
T250（contract test RED：POST /cases/{id}/trial-run-from-code API）
T251（Alembic migration：`case_chat_messages` 新增 `type` 欄位）
  ↓
T252（ChatMessage model 新增 `type` 欄位）    ← 可平行
  ↓
T253（ExecutionService 試跑流程）          ← 需 model 完成
T254（AI 失敗分析 prompt 組裝）            ← 可平行
  ↓
T255（CaseDetailPage Tab 2 試跑按鈕）      ← 可平行
T256（Chat 訊息渲染 trial_run_result 型別）
  ↓
T257（e2e 測試：完整試跑流程）
```

### 驗收條件

- `POST /cases/{id}/trial-run` 接受 `rf_code` 文字參數，無需先儲存案例
- 試跑完成後自動生成 `type='trial_run_result'` 訊息，持久化至 `case_chat_messages`
- 訊息 content 包含 `status` / `elapsed_ms` / `error_message` / `screenshot_paths`
- 試跑失敗時自動觸發 AI 分析，回應附加為新 `type='chat'` 訊息
- `GET /cases/{id}/chat-history` 回應包含 `type` 欄位，區分訊息型別
- CaseDetailPage Tab 2 的 RF 程式碼預覽區有明顯「立即試跑」按鈕
- 前端 Chat 區域可正確解析並顯示 `trial_run_result` 訊息（badge + 執行時間 + 錯誤訊息 + 截圖縮圖）
