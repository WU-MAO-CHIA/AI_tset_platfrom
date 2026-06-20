# Implementation Plan: 自動化測試平台 (Automatic Test Platform)

**Branch**: `001-auto-test-platform` | **Date**: 2026-06-20 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `specs/001-auto-test-platform/spec.md`

## Summary

全端自動化測試平台，測試人員可建立測試案例（含 AI 步驟補齊、Tab 分頁結構、RF 程式碼生成）、組成測試清單、透過 Robot Framework + Playwright 執行網頁測試、即時 SSE 進度推送，並以 RF 原生報告頁面嵌入展示結果。

**最新新增（2026-06-20）**：
- FR-003 第五排序欄：`version`（測試案例清單）
- FR-006 清單列表排序：`name`、`created_by`、`created_at` 三欄後端排序

## Technical Context

**Language/Version**: Python 3.11+ (backend) | Node.js 20+ / TypeScript 5 (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy (async), Alembic, Vue 3, Pinia, Vue Router 4, Axios, robotframework, robotframework-pabot, robotframework-browser, anthropic, openai, openpyxl  
**Storage**: SQLite (主資料庫, async via aiosqlite); 本地檔案系統（媒體附件、RF 腳本、執行報告）  
**Testing**: pytest + pytest-asyncio (backend); Vitest (frontend)  
**Target Platform**: Linux/Windows server, headless Chromium via Playwright  
**Project Type**: Web application (backend API + frontend SPA)  
**Performance Goals**: 清單篩選 ≤2s（千筆）; AI 補齊 ≤15s; RF 報告 ≤30s; trial run ≤60s  
**Constraints**: p95 ≤2s @ 10 concurrent users; 平行執行縮短 ≥40% vs 循序  
**Scale/Scope**: ~1000 測試案例, ~50 清單, ~10 並發使用者

## Constitution Check

*本專案無 constitution.md（`.specify/memory/constitution.md` 不存在），跳過此 Gate。*

## Project Structure

### Documentation (this feature)

```text
specs/001-auto-test-platform/
├── plan.md              # This file
├── research.md          # Phase 0 — 11 個技術決策
├── data-model.md        # Phase 1 — 實體與關係
├── quickstart.md        # Phase 1 — 整合測試情境
├── contracts/           # Phase 1 — API 規格
└── tasks.md             # Phase 2 — 任務清單（Phase 1–19）
```

### Source Code

```text
automatic_test/
├── backend/
│   ├── src/
│   │   ├── models/           # ORM models（test_case, checklist, execution_record, …）
│   │   ├── repositories/     # Generic + domain repositories
│   │   ├── services/         # Business logic（case, checklist, execution, ai, report, …）
│   │   ├── api/              # FastAPI routers（cases, checklists, executions, media, …）
│   │   ├── execution/        # RF Listener Plugin + Queue Registry
│   │   └── core/             # config, database, dependencies, llm_provider
│   ├── alembic/              # DB migrations
│   ├── robot_scripts/        # RF .robot 腳本（generated, results）
│   └── tests/                # pytest（unit, integration, contract, load）
├── frontend/
│   └── src/
│       ├── components/       # 共用元件（AIChatPanel, RFCodePreview, …）
│       ├── pages/            # 頁面（CasesPage, ChecklistsPage, ResultPage, …）
│       ├── services/         # API 呼叫（caseApi, checklistApi, executionApi）
│       └── stores/           # Pinia stores
└── specs/001-auto-test-platform/
```

**Structure Decision**: Web application (Option 2) — backend FastAPI + frontend Vue 3 SPA，分離部署，透過 Vite proxy 統一 API 路徑 `/api/v1/`。

## Key Research Decisions

| 決策 | 選擇 |
|------|------|
| LLM 多模型 | Provider 抽象層，Anthropic + OpenAI |
| RF 整合 | pabot + RF Listener Plugin + XML 解析 |
| 媒體儲存 | 本地檔案系統，路徑設定化 |
| 即時進度 | SSE + asyncio.Queue（RF Listener 寫入） |
| Excel/CSV | openpyxl + csv，標頭比對 + 預覽確認 |
| RF 代碼 | 實體 .robot 檔，`robot_scripts/{case_number}.robot` |
| RF 報告 | shutil.copytree → `data/execution_reports/{id}/`，FileResponse 服務 |

詳見 [research.md](./research.md)。

## Implementation Progress

**完成**：Phase 1–18（Setup → RF 報告嵌入 + 排序補齊）  
**待實作（Phase 19）**：  
- `version` 欄位加入 cases 排序（FR-003 第五欄）  
- checklists 列表後端排序（FR-006，三欄：name/created_by/created_at）

## Complexity Tracking

*無 Constitution 違規，此節跳過。*
