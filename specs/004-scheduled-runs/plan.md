# Implementation Plan: 排程執行

**Branch**: `004-scheduled-runs` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

## Summary

新增 `execution_schedules` 表與一個行程內的 `ScheduleRunner`（asyncio task，與 `ExecutionWorker` 一樣在
startup 開啟）。到期時呼叫既有的 `ExecutionService.run_checklist_parallel(...)` 排入 spec 003 的佇列，
執行本體、SSE、結果頁完全沿用。不新增服務，docker compose 不變。

```
ScheduleRunner（每 30 秒）
  └─ SELECT enabled AND next_run_at <= now
       └─ 條件式 UPDATE next_run_at = 下一次（搶到才繼續）
            ├─ 上一次仍 pending/running → last_skip_reason，不排入
            └─ ExecutionService.run_checklist_parallel(schedule_id=...) → execution_records(pending) → ExecutionWorker
```

## Technical Context

**Storage**: SQLite（既有），一張新表 + `execution_records` 一個欄位；只用標準型別（String / Integer / Boolean / JSON / DateTime(timezone=True)），之後換 PostgreSQL 不需改 schema
**時區**: 標準庫 `zoneinfo`；requirements 新增 `tzdata`（Windows 開發環境與 slim 映像沒有系統時區資料庫）
**Constraints**: 單一 uvicorn 行程；不新增 cron / APScheduler 等套件

## 資料模型（一個 Alembic migration）

### `execution_schedules`（新）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | String(36) PK | uuid |
| `checklist_id` | String(36) FK → test_checklists, index | 清單刪除時 ORM cascade 一併刪除 |
| `name` | String(100) | |
| `enabled` | Boolean, default true | |
| `frequency` | String(20) | `daily` / `weekly` / `interval` |
| `time_of_day` | String(5), nullable | `HH:MM`（daily / weekly） |
| `weekdays` | JSON, nullable | `[0..6]`，0 = 週一（weekly） |
| `interval_minutes` | Integer, nullable | ≥ 15（interval） |
| `parallel_mode` / `max_workers` | Boolean / Integer | 與手動執行相同，`max_workers` 受 `PARALLEL_MAX_WORKERS` 限制 |
| `next_run_at` | DateTime(tz), nullable, index | UTC；停用時為 null |
| `last_triggered_at` | DateTime(tz), nullable | |
| `last_execution_id` | String(36), nullable | 用來判斷「上一次是否未完成」與列表顯示上次狀態 |
| `last_skip_reason` | String(100), nullable | 例如「前一次仍在執行」 |
| `created_by` | String(100) | |
| `created_at` / `updated_at` | TimestampMixin | |

索引 `(enabled, next_run_at)`。

### `execution_records`（擴充）

- `schedule_id` String(36), nullable, index。不加 FK（排程刪除後記錄保留，前端顯示「已刪除的排程」），也避免 SQLite batch alter。

## 後端設計

### 1. 下次時間計算（`src/scheduling/timing.py`，純函式）

`compute_next_run(schedule, after: datetime) -> datetime`：在 `SCHEDULE_TIMEZONE` 下計算 `after` 之後的第一個時間點，回傳 UTC。
- daily：今天的 HH:MM 若已過則明天。
- weekly：往後 7 天內第一個符合 `weekdays` 的日子。
- interval：從 `after` 往後 `interval_minutes`。
以 `zoneinfo` 處理時區，單元測試涵蓋跨日、跨週、跨月。

### 2. `ScheduleRunner`（`src/scheduling/runner.py`）

- startup 時在 `ExecutionWorker` 之後開啟；shutdown 時取消。
- 每 30 秒 `tick(now)`：
  1. 查 `enabled AND next_run_at <= now`。
  2. 每筆：`UPDATE ... SET next_run_at=:next, last_triggered_at=:now WHERE id=:id AND next_run_at=:old`，
     rowcount 0 表示已被處理過，略過。`:next = compute_next_run(schedule, now)`——錯過的多次時間只會觸發這一次（Decision 2）。
  3. 若 `last_execution_id` 的狀態是 `pending` / `running` → 寫 `last_skip_reason`，不排入（Decision 3）。
  4. 否則呼叫 `ExecutionService(session).run_checklist_parallel(checklist_id, parallel_mode, max_workers, schedule_id=id)`，
     寫回 `last_execution_id`、清空 `last_skip_reason`。
  5. 每筆各自 try/except，失敗只記 log。
- `tick` 可直接在測試中以假時間呼叫，不需真的等待。

### 3. 觸發端

- `run_checklist_parallel` 新增 `schedule_id: Optional[str] = None` 參數，寫入記錄；其餘流程不變。

### 4. API（`src/api/schedules.py`）

| Method | Path | 權限 |
|---|---|---|
| GET | `/schedules` | 登入即可；含清單名稱、上次執行狀態 |
| GET | `/checklists/{id}/schedules` | 登入即可 |
| POST | `/checklists/{id}/schedules` | editor+ |
| PUT | `/schedules/{id}` | editor+；修改頻率或啟用時重算 `next_run_at` |
| DELETE | `/schedules/{id}` | editor+ |

驗證：`time_of_day` 為 `HH:MM`、weekly 至少一天、interval ≥ 15 分鐘、`max_workers` 1..`PARALLEL_MAX_WORKERS`。
執行記錄相關回應（清單執行歷史、執行詳情）加上 `schedule_id`、`schedule_name`。

### 5. 設定

`config.py` 新增 `schedule_timezone: str = "Asia/Taipei"`、`schedule_enabled: bool = True`（測試與除錯時可整個關閉排程器）；`.env.example` 與 README 補說明。

## 前端設計

- `services/scheduleApi.ts`：CRUD。
- `ChecklistDetailPage.vue`：新增「排程」區塊（列表 + 新增/編輯對話框：名稱、頻率選單、時間、星期勾選、間隔、平行設定、啟用開關），顯示下次 / 上次執行時間與狀態；viewer 唯讀。
- 新頁面 `/schedules`（`SchedulesPage.vue`）+ 導覽列入口：所有排程一覽，可快速啟用/停用。
- 執行頁、結果頁、清單執行歷史：`schedule_id` 有值時顯示「排程：<名稱>」標籤。

## 測試計畫

**後端（pytest，隔離 DB）**
- `compute_next_run`：daily / weekly / interval、跨日跨週、時區（Asia/Taipei 與 UTC 差 8 小時）
- `ScheduleRunner.tick`：到期排入 pending 且帶 `schedule_id`；未到期不動；條件式 UPDATE 防重複（同一 `now` 呼叫兩次只排入一次）；上一次 pending/running 時略過並記原因；錯過多次只補跑一次；停用不觸發；單筆例外不影響其他筆
- API：CRUD、驗證錯誤 400/422、viewer 403、刪除清單連帶刪除排程、修改頻率重算 `next_run_at`

**前端（Vitest）**
- 排程表單驗證與送出內容、列表顯示、viewer 唯讀、「排程觸發」標籤

## 分階段交付（每階段一個 PR）

1. **後端資料層 + 計算 + Runner**：migration、模型、`compute_next_run`、`ScheduleRunner`、`schedule_id`。合併後即可用 API 建立排程（尚無 UI）。
2. **後端 API**：排程 CRUD、執行回應帶排程資訊。
3. **前端**：清單頁排程區塊、排程一覽頁、「排程觸發」標籤。

（1 和 2 若改動不大可合為一個 PR。）

## 風險

- **SQLite 寫入**：排程器每 30 秒一次查詢、到期才寫，負擔可忽略。
- **時鐘與時區**：DB 內 `datetime.now()` 目前為 naive 本地時間（容器內即 UTC）；排程相關欄位一律以 aware UTC 寫入與比較，避免混用。
