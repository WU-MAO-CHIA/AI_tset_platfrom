# Implementation Plan: 自動化測試平台 (Automatic Test Platform)

**Branch**: `001-auto-test-platform` | **Date**: 2026-05-14 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/001-auto-test-platform/spec.md`

## Summary

建構一套基於瀏覽器操作的自動化測試平台，核心功能包含：測試案例 CRUD 管理（含 AI 多輪 Chat 對話介面、自動 RF 程式碼更新、多媒體附件）、測試清單組裝與執行排程、Robot Framework + Playwright 自動化執行引擎、SSE 即時進度推送、以及 HTML 測試報告產生與下載。後端採 FastAPI（Python 3.11+）+ SQLAlchemy 2.x async + SQLite，前端採 Vue 3 + TypeScript + Pinia。

測試案例建立／編輯畫面採 **Tab 分頁**結構：Tab 1「基本資訊」放置案例欄位；Tab 2「測試步驟」採左右分割——左側為 AI Chat 對話區（多輪對話氣泡），右側為 RF 程式碼自動預覽；對話歷史與案例一併持久化。**測試清單列表頁與詳情頁版面比照測試案例管理頁面**（相同的條列式結構、搜尋篩選、詳情版面）。

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.6+ (frontend)  
**Primary Dependencies**: FastAPI 0.115, Uvicorn, SQLAlchemy 2.0 (async), Alembic 1.13, aiosqlite, Robot Framework 7.1, robotframework-browser ≥18.9, Anthropic SDK, OpenAI SDK, Jinja2, Vue 3.5, Pinia 2.2, Vue Router 4.4, Axios 1.7, Vite 5.4  
**New (Phase 12)**: `case_chat_messages` DB table；後端 `/cases/{id}/chat` 多輪對話端點；前端 AIChatPanel 元件  
**Storage**: SQLite（開發 / 單機部署）via `aiosqlite`；Alembic 管理 schema 版本，7 個 migration 已套用  
**Testing**: pytest + pytest-asyncio（backend, asyncio_mode=auto）；vitest + @vue/test-utils（frontend）  
**Target Platform**: Windows / Linux 伺服器；後端提供 REST API，前端為 SPA  
**Project Type**: Web application（browser UI + REST API 後端）  
**Performance Goals**: 篩選結果 ≤2s（千筆）；AI 補齊 ≤15s；報告可查閱 ≤30s（執行完成後）  
**Constraints**: SQLite 單機；headless Chromium 安裝於後端伺服器；平行執行上限 5（可調）  
**Scale/Scope**: 10 位測試人員同時操作；案例數千筆規模

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First | ⚠️ VIOLATION (justified) | 本專案為完整 Web 應用程式，不適合拆解為獨立 library；見 Complexity Tracking |
| II. CLI Interface | ⚠️ VIOLATION (justified) | 主要介面為瀏覽器 UI + HTTP API；見 Complexity Tracking |
| III. Test-First (TDD) | ✅ PASS | 所有 tests 先寫入 RED 狀態，再實作至 GREEN |
| IV. Integration Testing | ✅ PASS | contract tests（httpx ASGITransport）+ integration tests |
| V. Simplicity / YAGNI | ✅ PASS | 無過度抽象；SSE 使用輪詢而非 pub/sub |
| VI. Develop Principles | ✅ PASS | SOLID/KISS；Service + Repository 分層；Vue + TypeScript |

**Post-Phase-1 Re-check**: 設計完成後無新違規。Complexity Tracking 已記錄並有業務理由。

## Project Structure

### Documentation (this feature)

```text
specs/001-auto-test-platform/
├── plan.md          # 本檔案
├── research.md      # Phase 0 技術選型決策
├── data-model.md    # Phase 1 資料模型
├── quickstart.md    # Phase 1 整合情境
├── contracts/       # Phase 1 API 合約（SSE、media、cases、checklists 等）
└── tasks.md         # 126 tasks（T001–T126 完成）+ Phase 12–13 待新增
```

### Source Code

```text
automatic_test/
├── backend/
│   ├── src/
│   │   ├── api/              # FastAPI 路由（cases, checklists, executions, media, llm_models, db_connections）
│   │   │                     # 【Phase 12】cases.py 新增：POST /cases/{id}/chat、GET /cases/{id}/chat-history
│   │   ├── core/             # config.py, database.py, llm_provider.py, dependencies.py
│   │   ├── models/           # SQLAlchemy ORM（TestCase, TestChecklist, ChecklistItem,
│   │   │                     #   ExecutionRecord, AutomationCode, CaseResult, ExecutionMedia,
│   │   │                     #   DBConnection, MediaAttachment, TestData,
│   │   │                     #   CaseChatMessage【Phase 12 新增】）
│   │   ├── repositories/     # TestCaseRepository, ChecklistRepository, ExecutionRepository
│   │   ├── services/         # CaseService, ChecklistService, ExecutionService, AIService,
│   │   │                     #   ReportService, DBConnectionService, MediaService, FileParserService
│   │   │                     # 【Phase 12】AIService 新增 chat_and_generate_rf()：多輪對話 + 同步回傳 rf_code
│   │   └── templates/        # report.html.j2（Jinja2 HTML 報告）
│   ├── tests/
│   │   ├── contract/         # test_cases_api, test_checklists_api, test_executions_api, test_db_connections_api
│   │   ├── integration/      # test_checklist_with_history, test_robot_execution
│   │   └── unit/             # test_case_service, test_ai_service_codegen, test_execution_service,
│   │                         #   test_report_service, test_db_connect_service, test_edge_cases
│   ├── alembic/              # 7 migrations
│   ├── data/                 # SQLite DB + media（runtime）
│   ├── robot_scripts/        # .robot 腳本（AI 生成，runtime）
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── components/       # TestCaseForm（Tab 1 欄位集合）, TestCaseList, MediaUploader,
    │   │                     #   LLMModelSelector,
    │   │                     #   AIChatPanel【Phase 12 新增】（Tab 2 左側：Chat 氣泡介面，
    │   │                     #     底部輸入框，多輪對話，AI 回應後自動觸發 RF 更新），
    │   │                     #   RFCodePreview（Tab 2 右側：RF 程式碼自動預覽），
    │   │                     #   ChecklistView, ExecutionProgress, ResultViewer
    │   ├── pages/            # CasesPage,
    │   │                     #   CaseCreatePage【Phase 12 重寫】（Tab 分頁：
    │   │                     #     Tab1→TestCaseForm，Tab2→AIChatPanel+RFCodePreview 左右分割）,
    │   │                     #   CaseDetailPage【Phase 12 重寫】（編輯模式同 CaseCreatePage Tab 結構）,
    │   │                     #   ChecklistsPage【Phase 13 重構】（版面比照 CasesPage）,
    │   │                     #   ChecklistDetailPage【Phase 13 重構】（版面比照 CaseDetailPage）,
    │   │                     #   ExecutionPage, ResultPage, DBConnectionPage
    │   ├── services/         # caseApi, checklistApi, executionApi, apiClient
    │   │                     # 【Phase 12】caseApi 新增 chatWithAI()、getChatHistory()
    │   ├── stores/           # executionStore（Pinia，SSE 狀態管理）
    │   └── router/           # index.ts（Vue Router）
    └── tests/
        └── unit/             # TestCaseForm.spec.ts, AIChatPanel.spec.ts【Phase 12 新增】
```

**Structure Decision**: Web application（Option 2）— backend + frontend 分離。後端 API 服務於 port 8000，前端 Vite dev server 於 port 5173（proxy `/api` → 8000）。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Library-First（I） | 平台需要完整 Web UI 供測試人員操作，無法以純 library 形式提供價值 | CLI-only 無法滿足即時進度顯示、媒體瀏覽、報告下載等 UX 需求 |
| CLI Interface（II） | 主介面為瀏覽器 SPA；後端提供 REST API，已涵蓋 text in/out 的精神 | 純 CLI 工具無法提供 SSE 即時推送與截圖瀏覽等 spec 明確要求的功能 |

## Phase 12: AI Chat 介面（Tab 分頁重構）

### 目標
將建立／編輯測試案例畫面重構為 Tab 分頁，Tab 2 實作 AI Chat 對話介面 + RF 程式碼自動預覽。

### 後端變更

| 項目 | 說明 |
|------|------|
| DB Migration | 新增 `case_chat_messages` 資料表（id, case_id, role, content, created_at） |
| Model | `CaseChatMessage`（SQLAlchemy ORM） |
| API | `POST /api/v1/cases/{id}/chat`：接收 user message + model，呼叫 LLM（帶歷史上下文），回傳 `{ assistant_message, rf_code }` |
| API | `GET /api/v1/cases/{id}/chat-history`：回傳該案例所有對話訊息 |
| AIService | 新增 `chat_and_generate_rf(messages, user_message, model)`：多輪對話 + 自動生成 RF code |

### 前端變更

| 項目 | 說明 |
|------|------|
| 新元件 | `AIChatPanel`：Chat 氣泡介面，底部輸入框，送出後呼叫 `/chat`，AI 回應氣泡顯示，同步 emit `rf-updated` 事件 |
| 重構 | `CaseCreatePage`：改為 Tab 分頁（Tab1: TestCaseForm + 儲存按鈕，Tab2: AIChatPanel + RFCodePreview 左右分割） |
| 重構 | `CaseDetailPage`：編輯模式改為與 CaseCreatePage 相同 Tab 結構 |
| 移除 | `StepsEditor` 元件（功能由 AIChatPanel 取代） |
| caseApi | 新增 `chatWithAI()`、`getChatHistory()` |

## Phase 13: 測試清單版面重構（比照測試案例管理）

### 目標
將測試清單列表頁（/checklists）與詳情頁（/checklists/:id）的版面結構對齊測試案例管理頁面。

### 前端變更

| 項目 | 說明 |
|------|------|
| 重構 | `ChecklistsPage`：採用與 `CasesPage` 相同的條列式清單版面（搜尋欄、篩選、表格列、可點入詳情） |
| 重構 | `ChecklistDetailPage`：採用與 `CaseDetailPage` 相同的版面結構（標題區＋動作按鈕、基本資訊區、項目列表區、歷史紀錄區） |
