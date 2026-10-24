# Implementation Plan: 執行佇列持久化（DB 佇列）

**Branch**: `003-persistent-execution-queue` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

## Summary

把「觸發即在記憶體裡跑」改成「觸發只寫 `pending` 記錄 → 背景 worker 從 DB 取工作 → 進度事件寫 DB →
SSE 從 DB 讀」。不新增任何服務，Docker Compose 不變，仍是單一 uvicorn worker。

```
POST /checklists/{id}/execute ─┐                     ┌─> execution_events ──> GET /executions/{id}/stream (SSE)
POST /cases/{id}/trial-run ────┴─> execution_records ─┤
                                  (status=pending)    └─ ExecutionWorker（啟動時開啟，asyncio task）
                                                          取 pending → running → 跑 robot/pabot → 寫結果與事件
```

## Technical Context

**Language/Version**: Python 3.13（backend）、TypeScript 5.6（frontend）
**Primary Dependencies**: FastAPI、SQLAlchemy 2.0 async、Alembic、Vue 3、Pinia
**Storage**: SQLite（既有），新增一張表、擴充一張表
**Testing**: pytest（`isolated_app` / 覆寫 `get_db`，不碰真實 DB）、Vitest unit
**Constraints**: 單一 uvicorn worker；SQLite 單一寫入者；事件格式需與現有前端相容

## 資料模型變更（一個 Alembic migration）

### `execution_records`（擴充）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `status` | 既有 | 新增合法值 `interrupted`、`cancelled`；`pending` 開始實際使用 |
| `params` | JSON, nullable | 觸發當下的快照：`case_ids`、`parallel_mode`、`max_workers`、`rf_code`（試跑覆寫）、`case_name` |
| `priority` | Integer, default 0 | 試跑 = 10、清單 = 0；取工作時 `ORDER BY priority DESC, queued_at ASC` |
| `queued_at` | DateTime | 觸發時間 |
| `heartbeat_at` | DateTime, nullable | worker 執行中每 15 秒更新 |

新增索引 `(status, priority, queued_at)`。

### `execution_events`（新）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | Integer PK autoincrement | 全域遞增，直接當 SSE 的 `id:`（`Last-Event-ID`） |
| `execution_id` | String(36), FK, index | |
| `event` | String(40) | `case_started` 等事件名 |
| `payload` | JSON | 與現在 `queue.put_nowait(...)` 的 dict 相同 |
| `created_at` | DateTime | |

索引 `(execution_id, id)`。

## 後端設計

### 1. 觸發端（`ExecutionService.run_checklist_parallel` / `run_trial`）

- 不再 `asyncio.create_task`。只建立記錄：`status=pending`、寫 `params` 快照、`priority`、`queued_at`，
  並寫一筆 `execution_queued` 事件。
- 空清單維持現在的行為：直接標 `completed`。
- API 回應與狀態碼不變（202 + `execution_id`），前端呼叫端不用改。

### 2. `ExecutionWorker`（新檔 `src/execution/worker.py`）

- `startup_event` 啟動：先跑 **恢復程序**，再開啟主迴圈 task；`shutdown` 時取消。
- **恢復程序**：`UPDATE execution_records SET status='interrupted', finished_at=now WHERE status='running'`，
  並為每筆寫 `execution_interrupted` 事件（`__done__: True`）。
- **主迴圈**：
  - 以 `asyncio.Semaphore(EXECUTION_MAX_CONCURRENT)` 控制同時執行數。
  - 有空位時領取下一筆：在一個交易內 `SELECT ... WHERE status='pending' ORDER BY priority DESC, queued_at LIMIT 1`，
    再 `UPDATE ... SET status='running', started_at=now WHERE id=:id AND status='pending'`，以 rowcount 判斷是否領到
    （為之後多 worker 預留；SQLite 單一寫入者下已足夠）。
  - 沒工作時等待 `asyncio.Event`（觸發端寫入後 `notify()`），另設 5 秒逾時兜底輪詢。
  - 每筆工作用獨立 task 執行，例外一律捕捉並標 `error`，不讓主迴圈停住。
  - 執行中每 15 秒更新 `heartbeat_at`。
- 執行本體沿用現有 `_execute_trial_bg` / `_execute_all_cases_bg` / `_run_sequential` / `_run_pabot`，
  改為從 `params` 讀參數，並把 `queue` 參數換成事件寫入器（見下）。
- 每筆開始前，替其他還在排隊的記錄更新 `execution_queued`（前面還有幾筆），讓排隊畫面會前進。

### 3. 事件寫入器（取代 `listener.py` 的記憶體佇列）

- 新增 `EventSink` 介面：`async emit(payload: dict)`，實作寫入 `execution_events` 並 commit。
- 現有程式中所有 `queue.put_nowait({...})` 改為 `await sink.emit({...})`，payload 內容不變。
- `listener.py` 的 `ExecutionListener` 目前沒有任何地方使用（pabot 進度是解析 `output.xml` 後送出），
  記憶體佇列相關函式隨第 2 階段移除。

### 4. SSE（`GET /executions/{id}/stream`）

- 認證維持 cookie。
- 讀取 `Last-Event-ID` header（或沒有則從 0 開始），每 1 秒查詢
  `SELECT * FROM execution_events WHERE execution_id=:id AND id > :last ORDER BY id`，逐筆送出
  `id: <id>\ndata: <payload>\n\n`。
- 收到 `__done__` 事件或記錄已在結束狀態且事件送完後關閉串流。
- 每 15 秒送 `: keep-alive` 註解行，避免 nginx 斷線（現有若已有則沿用）。

### 5. 取消（P3）

- `POST /executions/{id}/cancel`（editor 以上）：`UPDATE ... SET status='cancelled' WHERE id=:id AND status='pending'`；
  rowcount 0 時，若記錄存在回 409，不存在回 404。寫一筆 `execution_cancelled` 事件。

### 6. 設定與清理

- `config.py` 新增 `execution_max_concurrent: int = 1`，`.env.example` 與 README 補說明。
- `_cleanup_trial_runs` 一併刪除 30 天前的 `execution_events`。

## 前端設計

- `executionStore.ts`：`ExecutionStatus` 加上 `pending`、`interrupted`、`cancelled`；處理 `execution_queued`、
  `execution_interrupted`、`execution_cancelled` 事件。
- `ExecutionProgress`：`pending` 時顯示「排隊中（前面還有 N 筆）」與取消按鈕；`interrupted` / `cancelled` 顯示對應訊息。
- `ResultPage.vue`：`interrupted` / `cancelled` 視為已結束（與 `completed` / `failed` 同樣顯示結果與報告區）。
- 試跑結果面板（`AIChatPanel/TrialRunResult.vue`）：顯示排隊狀態。
- EventSource 的自動重連會帶 `Last-Event-ID`，不需額外處理。

## 測試計畫

**後端（pytest，全部使用隔離 DB）**
- worker 領取順序：試跑優先、同優先度依 `queued_at`
- 上限 1 時兩筆工作不會同時 `running`
- 恢復程序：`running` → `interrupted`、`pending` 保留並被執行
- 工作拋例外 → 標 `error`，下一筆照常執行
- SSE：從 DB 讀事件、`Last-Event-ID` 只補送之後的事件、`__done__` 後關閉
- 取消：`pending` 成功、`running` 回 409、不存在回 404、viewer 回 403
- 既有 `test_sse_stream.py` / `test_executions_api.py` 依新流程調整（不跳過）

**前端（Vitest）**
- 新狀態與事件在 `executionStore`、`ExecutionProgress`、`ResultPage` 的顯示

## 分階段交付（每階段一個 PR）

1. **資料層 + 恢復程序**：migration、模型、啟動時 `running` → `interrupted`。單獨合併就能解決「永遠執行中」。
2. **事件寫 DB + SSE 改讀 DB**：仍由觸發端直接執行，只換事件管道，風險最低。
3. **Worker 與排隊**：觸發端改寫 `pending`、worker、上限、優先度、`execution_queued`。
4. **前端新狀態 + 取消**。

## 風險

- **SQLite 寫入鎖**：事件寫入頻率不高（每個案例 2 筆），單一行程內可接受；若出現 `database is locked`，
  開啟 WAL 模式（`PRAGMA journal_mode=WAL`）。
- **SSE 改為輪詢 DB**：延遲上限約 1 秒，符合 SC-004。
- **既有測試依賴記憶體佇列**：需要一併改寫，第 2 階段處理。
