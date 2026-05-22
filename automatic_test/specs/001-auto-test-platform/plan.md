# Implementation Plan: 自動化測試平台 (Automatic Test Platform)

**Branch**: `001-auto-test-platform` | **Date**: 2026-05-14 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/001-auto-test-platform/spec.md`

## Summary

建構一套基於瀏覽器操作的自動化測試平台，核心功能包含：測試案例 CRUD 管理（含 AI 輔助步驟補齊與多媒體附件）、測試清單組裝與執行排程、Robot Framework + Playwright 自動化執行引擎、SSE 即時進度推送、以及 HTML 測試報告產生與下載。後端採 FastAPI（Python 3.11+）+ SQLAlchemy 2.x async + SQLite，前端採 Vue 3 + TypeScript + Pinia。

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.6+ (frontend)  
**Primary Dependencies**: FastAPI 0.115, Uvicorn, SQLAlchemy 2.0 (async), Alembic 1.13, aiosqlite, Robot Framework 7.1, robotframework-browser ≥18.9, Anthropic SDK, OpenAI SDK, Jinja2, Vue 3.5, Pinia 2.2, Vue Router 4.4, Axios 1.7, Vite 5.4  
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
└── tasks.md         # 102 tasks（全部完成）
```

### Source Code

```text
automatic_test/
├── backend/
│   ├── src/
│   │   ├── api/              # FastAPI 路由（cases, checklists, executions, media, llm_models, db_connections）
│   │   ├── core/             # config.py, database.py, llm_provider.py, dependencies.py
│   │   ├── models/           # SQLAlchemy ORM（TestCase, TestChecklist, ChecklistItem,
│   │   │                     #   ExecutionRecord, AutomationCode, CaseResult, ExecutionMedia,
│   │   │                     #   DBConnection, MediaAttachment, TestData）
│   │   ├── repositories/     # TestCaseRepository, ChecklistRepository, ExecutionRepository
│   │   ├── services/         # CaseService, ChecklistService, ExecutionService, AIService,
│   │   │                     #   ReportService, DBConnectionService, MediaService, FileParserService
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
    │   ├── components/       # TestCaseForm, TestCaseList, MediaUploader, LLMModelSelector,
    │   │                     #   ChecklistView, ExecutionProgress, ResultViewer
    │   ├── pages/            # CasesPage, CaseCreatePage, CaseDetailPage,
    │   │                     #   ChecklistsPage, ChecklistDetailPage,
    │   │                     #   ExecutionPage, ResultPage, DBConnectionPage
    │   ├── services/         # caseApi, checklistApi, executionApi, apiClient
    │   ├── stores/           # executionStore（Pinia，SSE 狀態管理）
    │   └── router/           # index.ts（Vue Router）
    └── tests/
        └── unit/             # TestCaseForm.spec.ts
```

**Structure Decision**: Web application（Option 2）— backend + frontend 分離。後端 API 服務於 port 8000，前端 Vite dev server 於 port 5173（proxy `/api` → 8000）。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Library-First（I） | 平台需要完整 Web UI 供測試人員操作，無法以純 library 形式提供價值 | CLI-only 無法滿足即時進度顯示、媒體瀏覽、報告下載等 UX 需求 |
| CLI Interface（II） | 主介面為瀏覽器 SPA；後端提供 REST API，已涵蓋 text in/out 的精神 | 純 CLI 工具無法提供 SSE 即時推送與截圖瀏覽等 spec 明確要求的功能 |
