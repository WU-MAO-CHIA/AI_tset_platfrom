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
| 25 | 測資變數四欄表格 + 清單案例展開列（FR-001/005/006/023） | 🔄 進行中 |

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
