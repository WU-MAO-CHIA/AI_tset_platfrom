# Implementation Plan: 自動化測試平台 (Automatic Test Platform)

**Branch**: `001-auto-test-platform` | **Date**: 2026-06-21 | **Spec**: [spec.md](./spec.md)  
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

*本專案無 `.specify/memory/constitution.md`，跳過此 Gate。*

## Project Structure

### Documentation (this feature)

```text
specs/001-auto-test-platform/
├── plan.md              # This file
├── research.md          # Architecture decisions (Decision 1–12)
├── data-model.md        # Entity definitions
├── quickstart.md        # Integration scenarios
├── contracts/           # API contracts
└── tasks.md             # Task breakdown
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

### 已完成 Phase 1–19

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

### Phase 20：登入畫面 + 管理後台（FR-024〜FR-027）

**目標**：
1. 登入畫面（/login）+ JWT 驗證 middleware
2. 三角色 RBAC（admin / editor / viewer）
3. 管理後台（/admin）：帳號管理、系統別管理、LLM API Key 管理
4. 初始管理員 seed script

**詳見 tasks.md Phase 20 任務清單。**
