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
| 20 | 登入畫面 + JWT 驗證 + 三角色 RBAC + 管理後台 | ✅ |

### Phase 22：執行前空清單驗證（FR-009 pre-flight）

**目標**：點擊「執行測試」前，前端先檢查清單中案例數是否 > 0；若為 0 則顯示警示提示，不觸發後端請求。

**涉及檔案**：
- `automatic_test/frontend/src/pages/ChecklistDetailPage.vue`（執行按鈕 click handler 加入前置檢查）

**驗收條件**：測試清單無案例時，點擊「執行測試」後顯示警示訊息「測試清單為空，請先新增案例」，瀏覽器 Network tab 無 POST 請求發出。

### Phase 23：LLM API Key 帶出遮罩 + 全域預設模型（FR-027 / FR-012）

**目標**：
1. `/admin` LLM 分頁載入時「帶出」各 provider 目前已儲存的 API Key，以**遮罩**呈現（前 7 字元 + 末 4 碼），**禁回傳明文**。
2. `/admin` 新增「**全域預設模型**」下拉選擇，持久化於 `app_setting`，覆蓋 env `default_llm_model`，立即生效、無需重啟。
3. 建立案例頁移除寫死的 `'claude-sonnet-4-6'`，改讀全域預設模型；模型切換僅於 `/admin`，表單不提供選擇器。

**設計決策**：
- 全域預設模型沿用既有 `AppSetting`（key=`default_llm_model`，存於 `encrypted_value` 欄）儲存，**不需 Alembic migration**；雖非機密，沿用加密欄可避免 schema 變更。
- 遮罩採後端產生：解密後僅輸出「前 7 字元 + `****…` + 末 4 碼」（如 `sk-ant-****…dF3a`；金鑰長度 < 12 時整串 `****`），API 永不回傳完整金鑰（符合 FR-027 / FR-007 加密原則）。
- 全域預設模型下拉僅列出對應 provider 已設定 API Key 的可用模型（`requires_setup=false`），避免選到無 Key 的模型導致 AI 補齊失敗。
- 依 constitution III（Test-First, NON-NEGOTIABLE）：Phase 23 先寫 contract/unit test（確認 RED）再實作。
- `/llm-models` 的 `default` 改為 **DB 優先**（讀 `app_setting.default_llm_model`），無則 fallback 至 env。

**後端修改範圍**：

| 檔案 | 變更 |
|------|------|
| `services/app_setting_service.py` | `get_llm_keys()` 改回傳含遮罩值（`*_key_set` 保留 + 新增 `*_key_masked`）；新增 `get_default_model()` / `set_default_model()`；新增 `_mask(key)` helper |
| `api/admin.py` | `GET /llm-keys` 回傳遮罩值；新增 `GET /admin/llm-default-model`、`PUT /admin/llm-default-model` |
| `api/llm_models.py` | `default` 改讀 `app_setting`（DB）優先，無則 fallback `settings.default_llm_model` |
| LLM 呼叫端（AI 補齊 / Chat / RF 代碼生成 service） | 未顯式指定模型時，改用全域預設模型（DB） |

**前端修改範圍**：

| 檔案 | 變更 |
|------|------|
| `services/adminApi.ts` | `LlmKeyStatus` 增 `*_key_masked`；新增 `getDefaultModel()` / `setDefaultModel(modelId)` 與型別 |
| `pages/AdminPage.vue` | LLM 分頁顯示遮罩 key（已設定時於狀態列呈現 `sk-ant-****…dF3a`）；新增「全域預設模型」下拉（選項來源 `/llm-models`），儲存呼叫 `setDefaultModel` |
| `pages/CaseCreatePage.vue` | 移除寫死 `selectedModel = ref('claude-sonnet-4-6')`，改於 `onMounted` 讀 `/llm-models` 的 `default` |
| 死碼移除 | 刪除 `components/StepsEditor/` 與 `components/LLMModelSelector/`（全前端零引用） |

**驗收條件**：
- `/admin` LLM 分頁載入即顯示已設定 key 的遮罩（如 `sk-ant-****…dF3a`）；未設定顯示「未設定」；API 回應不含完整金鑰。
- `/admin` 切換全域預設模型並儲存後，新建案例的 AI 補齊／RF 生成即採用該模型，無需重啟。
- 建立案例頁不再寫死模型，畫面無模型選擇器；`/llm-models` 的 `default` 反映 DB 設定值。

### Phase 20：登入畫面 + 管理後台（FR-024〜FR-027）

**目標**：
1. 登入畫面（/login）+ JWT 驗證 middleware
2. 三角色 RBAC（admin / editor / viewer）
3. 管理後台（/admin）：帳號管理、系統別管理、LLM API Key 管理
4. 初始管理員 seed script

**詳見 tasks.md Phase 20 任務清單。**

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

**架構決策**：

```
執行路由：
  execution_mode == 'local'  → 現行本地 robot CLI 邏輯（不變）
  execution_mode == 'remote' → .robot 加入 Remote Library → robot CLI
                               → RF 透過 XML-RPC 連到 Remote Server
                               → Keyword 在 Remote Server 執行
                               → 結果回傳本地，報告照常產生
```

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

**Pre-flight 安全機制**（執行前自動檢查）：
```python
# ExecutionService：若案例包含 remote，先 ping Remote Server
if any(c.execution_mode == 'remote' for c in cases):
    url = await app_setting_service.get_remote_server_url()
    if not url:
        raise RuntimeError("Remote Server URL 未設定")
    try:
        server = xmlrpc.client.ServerProxy(url)
        server.get_keyword_names()
    except Exception:
        raise RuntimeError(f"Remote Server {url} 連線失敗，請確認已啟動")
```

**注意事項**：
- Remote Server 需預先手動啟動（不在本平台管理範圍）
- XML-RPC 預設無驗證，建議限制 Remote Server 僅接受內網 IP
- pabot 平行執行時，多個 remote case 會同時連接同一 Remote Server，需確認 Server 支援並發呼叫
