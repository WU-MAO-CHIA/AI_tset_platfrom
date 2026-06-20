# Implementation Plan: 自動化測試平台

**Branch**: `001-auto-test-platform` | **Date**: 2026-06-20 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `specs/001-auto-test-platform/spec.md`

## Summary

自動化測試平台，提供測試案例 CRUD（含 AI 輔助步驟補齊 + Chat 介面）、測試清單管理、Robot Framework + Playwright 執行引擎、SSE 即時執行進度推送、結果報告呈現與匯出等完整流程。技術棧：FastAPI（async）+ SQLAlchemy 2.0 + aiosqlite（後端 API）、Vue 3 + Pinia（SPA 前端）、Robot Framework + pabot + Playwright（執行引擎）、Anthropic / OpenAI SDK（LLM 整合）。

## Technical Context

**Language/Version**: Python 3.11+ (backend)，TypeScript 5.x / Vue 3.4+ (frontend)  
**Primary Dependencies**:
- Backend: FastAPI 0.115+, SQLAlchemy 2.0 (async), aiosqlite, alembic, pydantic-settings, Robot Framework 7+, robotframework-pabot, robotframework-browser, playwright, anthropic SDK, openai SDK, openpyxl, aiofiles
- Frontend: Vue 3, Vite 5, Vue Router 4, Pinia 2, Axios

**Storage**:
- SQLite（`data/autotest.db`）— 透過 aiosqlite + SQLAlchemy async 存取
- 本地檔案系統：
  - `data/media/` — 測試案例多媒體附件（圖片/影片）
  - `data/execution_reports/{execution_id}/` — RF 原生執行報告（`log.html`、`report.html`、`output.xml`）；執行完成後由 `shutil.copytree` 從 tempdir 複製，由 FastAPI FileResponse 服務
  - `robot_scripts/` — 各案例的 `.robot` 執行腳本（`{case_number}.robot`）

**報告類型說明**（兩種，不可混淆）:
- **FR-011 匯出報告**：後端 Jinja2 模板渲染的自包含 HTML，供下載（`GET /executions/{id}/export`）
- **FR-010/FR-019 嵌入報告**：RF 原生 `log.html` / `report.html`，於結果頁面「RF 報告」Tab 以 `<iframe>` 嵌入（`GET /executions/{id}/rf-report/{filename}`）

**Testing**: pytest + pytest-asyncio（後端）；前端目前無 unit test 規劃  
**Target Platform**: Web application（Chrome latest），server 可 Linux / Windows  
**Project Type**: Web service（FastAPI REST API）+ SPA（Vue 3 / Vite）  

**Performance Goals**:
- SC-002: 關鍵字搜尋結果 < 2s（千筆案例規模）
- SC-005: 報告在執行完成後 30s 內可查閱/下載
- SC-006: 10 位使用者同時操作 p95 頁面回應 < 2s
- SC-007: AI 步驟補齊 < 15s
- SC-010: RF 代碼生成 < 35s，失敗率 < 5%
- SC-011: 立即試跑 < 60s（含 RF 執行）

**Constraints**:
- SQLite 不支援高並發寫入（async session 需分離，background task 不得重用 request-scoped session）
- pabot 並行數由 `PARALLEL_MAX_WORKERS` 控制（預設 5）
- SSE polling 需每輪開新 session（SQLite transaction isolation 問題，見 research.md 決策 9）

**Scale/Scope**: ~1000 筆測試案例，~10 位同時使用者，單一組織

## Constitution Check

*constitution.md 不存在，跳過 gate 檢查。*

## Project Structure

### Documentation (this feature)

```text
specs/001-auto-test-platform/
├── plan.md              # This file
├── research.md          # Phase 0 — 技術決策與研究結果
├── data-model.md        # Phase 1 — 實體關係模型
├── quickstart.md        # Phase 1 — 環境設定與整合情境
├── contracts/           # Phase 1 — API & SSE 契約
│   ├── api.md
│   └── sse.md
└── tasks.md             # Phase 2 — 實作任務清單（/speckit-tasks 產出）
```

### Source Code

```text
automatic_test/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── cases.py            # 測試案例 CRUD + AI + RF script + 試跑
│   │   │   ├── checklists.py       # 清單管理 + 案例管理 + 執行觸發
│   │   │   ├── executions.py       # 執行紀錄查詢 + SSE stream + 報告匯出
│   │   │   ├── db_connections.py   # 外部 DB 連線管理
│   │   │   └── media.py            # 媒體檔案服務
│   │   ├── core/
│   │   │   ├── config.py           # pydantic-settings（.env）
│   │   │   ├── database.py         # AsyncSessionLocal + get_db
│   │   │   └── llm_provider.py     # LLM Provider 抽象層
│   │   ├── models/                 # SQLAlchemy ORM 模型
│   │   ├── repositories/           # DB 存取層（Repository pattern）
│   │   └── services/               # 商業邏輯層
│   │       ├── execution_service.py  # 背景執行（asyncio.create_task + 獨立 session）
│   │       ├── ai_service.py         # LLM 呼叫（步驟補齊 / RF 代碼生成 / Chat）
│   │       └── report_service.py     # output.xml 解析 + HTML 報告生成
│   ├── data/
│   │   └── autotest.db
│   ├── robot_scripts/              # {case_number}.robot 實體檔案
│   ├── alembic/                    # DB 遷移腳本
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── load/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AIChatPanel/        # Tab 2 左側 Chat 介面
│   │   │   ├── RFCodePreview/      # Tab 2 右側 RF 程式碼預覽 + 儲存
│   │   │   ├── ExecutionProgress/  # SSE 即時進度元件
│   │   │   ├── StepsEditor/        # 測試步驟編輯器
│   │   │   └── ResultViewer/       # 執行結果展示
│   │   ├── pages/
│   │   │   ├── CasesPage.vue
│   │   │   ├── CaseDetailPage.vue
│   │   │   ├── CaseCreatePage.vue
│   │   │   ├── ChecklistsPage.vue
│   │   │   ├── ChecklistDetailPage.vue
│   │   │   ├── ChecklistCasesPage.vue
│   │   │   ├── ExecutionPage.vue
│   │   │   └── ResultPage.vue             # 執行結果頁（含「RF 報告」Tab + iframe）
│   │   ├── services/               # Axios API wrappers
│   │   └── stores/
│   │       └── executionStore.ts   # Pinia — SSE 執行進度狀態
│   └── tests/
└── specs/
    └── 001-auto-test-platform/
```

**Structure Decision**: Web application（Option 2）— backend/ REST API + frontend/ SPA，透過 Vite proxy 在開發模式下橋接 `/api`。

## Complexity Tracking

| 決策 | 理由 | 簡單替代方案被拒原因 |
|------|------|----------------------|
| asyncio.create_task 背景執行（非 FastAPI BackgroundTasks） | 需要長時間執行任務（>60s RF 執行）超出 HTTP 請求生命週期 | FastAPI BackgroundTasks 仍在 request 結束前執行，不適合 long-running |
| SSE polling 每輪開新 session | SQLite WAL 下同一 session 的 read transaction 快照不反映其他 session 的 commit | 在同一 session 內 expire/refresh 無法解決 SQLite 的 transaction isolation |
| RF script 存為實體檔案（非 DB column） | Robot Framework CLI 執行需要實體 .robot 檔；避免每次執行前重新生成 | DB TEXT 欄位存 RF 代碼雖可行，但每次執行仍需寫出為臨時檔案，不如直接持久化 |
| RF 報告 shutil.copytree 至持久化目錄 | tempfile.TemporaryDirectory 在 with block 結束後自動刪除，必須在此前複製 log.html/report.html | 將 --outputdir 直接指向持久化路徑：並行執行時多案例會互相覆蓋 |
