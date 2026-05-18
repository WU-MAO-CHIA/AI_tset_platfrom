# Implementation Plan: 自動化測試平台 (Automatic Test Platform)

**Branch**: `001-auto-test-platform` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-auto-test-platform/spec.md`

## Summary

建立一個 Web 自動化測試平台，涵蓋：測試案例 CRUD（含版本管理、LLM 輔助步驟補齊、多媒體附件、建立後即時試跑）、測試清單管理（含執行歷史）、Excel/CSV 測試參數匯入、外部 SQLite 資料庫串接、AI 代碼生成 + 平行網頁測試執行，以及結構化執行結果的網頁呈現（含截圖/影片）。

技術方向：Python 3.14 後端（FastAPI + SQLAlchemy + Robot Framework）、TypeScript + Vue 3 前端；TDD 強制執行；Library-First 架構，每個核心功能域包裝為獨立 service/repository 模組。

## Technical Context

**Language/Version**: Python 3.14 (backend) + TypeScript (frontend)
**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2.x, Alembic, Robot Framework, Playwright (RF library), httpx, python-multipart, aiofiles
- Frontend: Vue 3 + Composition API, TypeScript, Pinia, Vue Router, Axios, VueUse
- LLM: Anthropic SDK / OpenAI SDK (可切換，透過 provider 抽象層)
- Testing: pytest + pytest-asyncio (backend), Vitest + Vue Test Utils (frontend)

**Storage**:
- Primary DB: SQLite（開發/生產初期）→ 可遷移至 PostgreSQL（SQLAlchemy 抽象）
- File Storage: 本地檔案系統（媒體附件 + 執行結果截圖/影片），路徑設定化
- Test Result: Robot Framework XML → 解析後存入 DB，XML 原始檔保留

**Testing**: pytest (unit + integration + contract), Vitest (frontend unit), playwright test (e2e)
**Target Platform**: Web 應用程式（瀏覽器存取），部署於 Linux server
**Project Type**: Web application（frontend SPA + backend REST API + background task engine）
**Performance Goals**:
- 篩選清單：千筆案例 ≤2s
- AI 補齊：≤15s（LLM API 依賴）
- 代碼生成：≤30s，失敗率 <5%
- 平行執行效能提升：≥40%（≥10 案例清單）
- 結果頁面載入：≤10s（含前 50 截圖縮圖）
- 試跑完成：≤60s

**Constraints**:
- 無需客戶端安裝（瀏覽器存取）
- 圖片附件 ≤10MB；影片附件 ≤100MB
- 平行執行預設並行數 5（管理員可設定）
- LLM API 金鑰由管理員統一設定，不暴露給個別使用者
- 測試案例刪除採軟刪除（保留歷史報告可查閱）

**Scale/Scope**: 10 位同時操作的測試人員，千筆案例規模，每次執行最多數十個案例

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First | ✅ PASS | 各功能域（case_service, checklist_service, execution_engine, ai_service, report_service）各自獨立，可單獨測試 |
| II. CLI Interface | ✅ PASS（豁免已記錄） | 本專案為 Web application，FastAPI HTTP 端點作為 CLI 等價介面（request body = stdin，response body = stdout，HTTP 狀態碼 = exit code）；`python -m xxx` 腳本模式適用於 library 型專案，不適用 REST API 服務。豁免已記錄於 Complexity Tracking。 |
| III. Test-First (NON-NEGOTIABLE) | ✅ PASS | 所有 tasks 遵循 Red-Green-Refactor；failing tests 須先存在才能開始 implement |
| IV. Integration Testing | ✅ PASS | DB 操作、LLM API、Robot Framework 執行、檔案 I/O 均需 integration tests |
| V. Simplicity (YAGNI) | ✅ PASS | 不預先建 plugin 系統；LLM provider 抽象僅在確認多模型需求時引入 |
| VI. Develop Principles | ✅ PASS | SOLID + KISS + Python 3.14 + Service/Repository + TypeScript/Vue |

**Complexity Tracking**:

| 原則 | 豁免項目 | 理由 |
|------|---------|------|
| II. CLI Interface | `python -m xxx` CLI 腳本 | 本專案為 Web application；FastAPI HTTP 端點等同 CLI 介面（stdin/stdout 對應 request/response），`python -m` 模式適用 library 型專案，於此架構不具實質效益 |

## Project Structure

### Documentation (this feature)

```text
specs/001-auto-test-platform/
├── plan.md              ← 本文件
├── research.md          ← Phase 0 輸出
├── data-model.md        ← Phase 1 輸出
├── quickstart.md        ← Phase 1 輸出
├── contracts/           ← Phase 1 輸出
│   ├── api.md           ← REST API 合約
│   └── websocket.md     ← WebSocket 合約（即時進度）
└── tasks.md             ← Phase 2 輸出（/speckit-tasks 生成）
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── test_case.py
│   │   ├── test_checklist.py
│   │   ├── execution_record.py
│   │   ├── test_report.py
│   │   └── db_connection.py
│   ├── repositories/        # Repository pattern — DB CRUD 封裝
│   │   ├── test_case_repo.py
│   │   ├── checklist_repo.py
│   │   └── execution_repo.py
│   ├── services/            # Business logic
│   │   ├── case_service.py        # 測試案例 CRUD + 版本管理
│   │   ├── checklist_service.py   # 測試清單管理
│   │   ├── ai_service.py          # LLM 整合（補齊/代碼生成）
│   │   ├── execution_service.py   # 測試執行（RF 呼叫 + 平行）
│   │   ├── report_service.py      # 測試結果解析與儲存
│   │   ├── db_connect_service.py  # 外部 DB 串接
│   │   └── media_service.py       # 媒體附件 + 執行截圖管理
│   ├── api/                 # FastAPI routers
│   │   ├── cases.py
│   │   ├── checklists.py
│   │   ├── executions.py
│   │   ├── reports.py
│   │   └── db_connections.py
│   ├── core/
│   │   ├── config.py        # 設定（DB path、media path、LLM keys）
│   │   ├── database.py      # SQLAlchemy engine + session
│   │   └── dependencies.py  # FastAPI dependency injection
│   └── main.py              # FastAPI app entry
│
└── tests/
    ├── unit/                # 純邏輯，mock 外部依賴
    ├── integration/         # 真實 DB + 真實服務互動
    └── contract/            # API 合約測試

frontend/
├── src/
│   ├── components/          # 可重用 UI 元件
│   │   ├── TestCaseForm/
│   │   ├── TestCaseList/
│   │   ├── ChecklistView/
│   │   ├── ExecutionProgress/
│   │   ├── ResultViewer/
│   │   └── MediaUploader/
│   ├── pages/               # 路由頁面
│   │   ├── CasesPage.vue
│   │   ├── CaseDetailPage.vue
│   │   ├── ChecklistsPage.vue
│   │   ├── ExecutionPage.vue
│   │   └── ResultPage.vue
│   ├── services/            # API client
│   │   ├── caseApi.ts
│   │   ├── checklistApi.ts
│   │   ├── executionApi.ts
│   │   └── reportApi.ts
│   ├── stores/              # Pinia state
│   │   ├── caseStore.ts
│   │   └── executionStore.ts
│   └── types/               # TypeScript 型別定義
│
└── tests/
    ├── unit/
    └── e2e/

robot_scripts/               # Robot Framework .robot 檔案（AI 生成後存放）
├── generated/               # AI 生成的 .robot 檔
└── results/                 # RF 執行輸出（XML、截圖、影片）
```

**Structure Decision**: 採 Option 2（Web application）。backend 為獨立 Python 套件，frontend 為獨立 Vue 3 SPA；robot_scripts 為執行引擎工作目錄，與後端分離但由 execution_service 管理。

## Complexity Tracking

> 無 Constitution 違規需記錄。
