# Implementation Plan: 自動化測試平台

**Branch**: `001-auto-test-platform` | **Date**: 2026-06-13 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/001-auto-test-platform/spec.md`

## Summary

建立完整的自動化測試平台，涵蓋測試案例 CRUD（含 AI 輔助步驟補齊、Tab 分頁 UI）、測試清單管理、外部資料庫串接、Robot Framework 自動執行與報告產生。前端採 Vue 3 + TypeScript，後端採 FastAPI + Python 3.11+，使用 SQLite 儲存，Playwright 驅動瀏覽器測試。技術決策詳見 [research.md](research.md)。

## Technical Context

**Language/Version**: Python 3.11+ (backend)、TypeScript 5+ (frontend)  
**Primary Dependencies**: FastAPI、SQLAlchemy（async）、Pydantic v2（backend）；Vue 3、Vite、Vue Router 4（frontend）；Robot Framework + **robotframework-pabot**（平行執行）+ robotframework-browser（Playwright-based，截圖/影片）；Anthropic SDK + OpenAI SDK（AI 整合）；cryptography（DB 憑證加密）  
**Storage**: SQLite（透過 SQLAlchemy async ORM）；媒體附件存 filesystem `uploads/`，DB 僅記錄路徑  
**Testing**: pytest + pytest-asyncio（backend）；vitest + Playwright E2E（frontend）  
**Target Platform**: Linux server（backend）+ Chrome/Edge 最新版（frontend）  
**Project Type**: Web application（frontend + backend 分離，Option 2 split structure）  
**Performance Goals**: AI 補齊 < 15s (SC-007)；AI 代碼生成 < 35s (SC-010)；試跑 < 60s (SC-011)；頁面操作 p95 < 2s (SC-006)；篩選 < 2s / 千筆 (SC-002)  
**Constraints**: 10+ 並行使用者；平行執行預設 5 案例同時進行；圖片 ≤ 10MB、影片 ≤ 100MB  
**Scale/Scope**: 千筆案例規模，10 位測試人員並行操作

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Library-First | ⚠ JUSTIFIED | 整合性 Web 應用；各 Service 模組具清楚邊界與單一職責，扮演可重用 Library 角色 |
| CLI Interface | ⚠ DEFERRED | 核心服務透過 HTTP API 暴露；CLI 封裝屬後續工作，不在 MVP scope |
| Test-First (TDD) | ✅ REQUIRED | 所有新功能必須先寫測試（RED），通過審核後才實作（GREEN） |
| Integration Testing | ✅ REQUIRED | API 合約測試、AI service 整合、RF 執行整合 |
| Simplicity (YAGNI) | ✅ PASS | SQLite 優先；Repository 模式有明確多端查詢需求支撐 |
| SOLID/KISS | ✅ PASS | model / repository / service / API handler 各層職責分離 |
| Python 3.11+ | ✅ PASS | backend 使用 Python 3.11+ |
| TypeScript + Vue | ✅ PASS | frontend 使用 Vue 3 + TypeScript |

## Project Structure

### Documentation (this feature)

```text
specs/001-auto-test-platform/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output — technical decisions
├── data-model.md        # Phase 1 output — entity & relationship definitions
├── quickstart.md        # Phase 1 output — integration scenarios
├── contracts/           # Phase 1 output — REST API contracts
│   ├── api-cases.md
│   ├── api-checklists.md
│   ├── api-executions.md
│   └── api-db-connections.md
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code

```text
automatic_test/
├── backend/
│   ├── src/
│   │   ├── api/              # FastAPI routers
│   │   │   ├── cases.py      # /api/v1/cases
│   │   │   ├── checklists.py # /api/v1/checklists
│   │   │   ├── db_connections.py  # /api/v1/db-connections
│   │   │   ├── executions.py # /api/v1/executions
│   │   │   ├── media.py      # /api/v1/media
│   │   │   └── llm_models.py # /api/v1/llm-models
│   │   ├── core/             # config, database, dependencies, llm_provider
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── repositories/     # DB query wrappers (CRUD)
│   │   └── services/         # Business logic services
│   └── tests/
│       ├── contract/         # API contract tests (TDD-first)
│       ├── integration/      # Service integration tests
│       └── unit/             # Unit tests
│
└── frontend/
    ├── src/
    │   ├── components/       # Reusable Vue components
    │   │   ├── AIChatPanel/  # AI 對話介面
    │   │   ├── RFCodePreview/  # RF 程式碼預覽
    │   │   ├── TestCaseForm/ # 測試案例表單（Tab 1）
    │   │   ├── FileImporter/ # 測試資料匯入
    │   │   └── ...
    │   ├── pages/            # Page-level Vue components
    │   │   ├── CasesPage.vue
    │   │   ├── CaseCreatePage.vue
    │   │   ├── CaseDetailPage.vue
    │   │   ├── ChecklistsPage.vue
    │   │   ├── ChecklistDetailPage.vue
    │   │   ├── DBConnectionPage.vue
    │   │   └── ...
    │   └── services/         # API client (caseApi, etc.)
    └── tests/
```

**Structure Decision**: Web application（Option 2）。前後端各自獨立，透過 REST API 通訊；前端 SPA 由 Vite 建置，後端以 FastAPI async 運行。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Library-First exemption | 整合性 Web 平台，整個系統即產品 | 拆成獨立 library 增加部署複雜度，與 MVP 時程不符 |
| CLI Interface deferred | HTTP API 即服務介面 | CLI 封裝未在 spec 要求，屬後續增強工作 |
| Repository pattern | 多個 endpoint 共享相同查詢邏輯（list/filter/CRUD） | 直接 DB 存取會導致重複查詢邏輯分散在各 service |
