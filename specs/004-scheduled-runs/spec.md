# Feature Specification: 排程執行

**Feature Branch**: `004-scheduled-runs`
**Created**: 2026-10-25
**Status**: Draft
**Input**: 「開始排程執行」——讓測試清單可以依排程自動執行（spec 003 Out of Scope 中的「排程觸發，會建立在這個佇列之上」）

## 背景

目前清單只能由使用者按「執行」觸發。spec 003 之後，觸發端只寫一筆 `pending` 記錄，由
`ExecutionWorker` 依序領取執行。排程只要在時間到時「代替使用者觸發一次」，排入同一個佇列即可，
不需要另外的執行管道，也不需要額外服務（cron、Redis、Celery 等）。

部署環境是一台 Oracle A1 VM、docker compose、單一 uvicorn 行程，因此排程器同樣是後端行程內的一個
asyncio task，排程定義與下次執行時間存在 DB，重啟後可接續。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 每天固定時間自動跑回歸清單 (Priority: P1)

測試人員替「每日回歸」清單設定「每天 02:00」，之後不必有人在場，系統每天 02:00 自動排入一次執行，
早上進來就能看到結果。

**Independent Test**: 建立一個「下一次執行時間」為一分鐘後的排程，一分鐘後該清單出現一筆新的執行記錄，標記為排程觸發。

**Acceptance Scenarios**:

1. **Given** 清單有一個啟用中的排程「每天 02:00」，**When** 時間到 02:00，**Then** 系統排入一筆該清單的執行（與手動觸發相同，進入 spec 003 的佇列），記錄標示「排程：<排程名稱>」
2. **Given** 排程已觸發，**When** 使用者查看排程列表，**Then** 看得到「上次執行時間 / 結果」與「下次執行時間」
3. **Given** 佇列中已有其他執行，**When** 排程觸發，**Then** 排程的執行照常排隊（與手動清單執行同優先度，低於試跑）

### User Story 2 - 管理排程 (Priority: P1)

editor 以上可以在清單頁新增、修改、停用/啟用、刪除排程；viewer 只能查看。

**Acceptance Scenarios**:

1. **Given** editor 在清單頁，**When** 新增排程並選擇頻率，**Then** 儲存後立即顯示計算出的「下次執行時間」
2. **Given** 一個啟用中的排程，**When** 使用者停用它，**Then** 時間到不再觸發；重新啟用後，下次執行時間從「現在」往後重算（不補跑停用期間）
3. **Given** viewer，**When** 呼叫新增/修改/刪除 API，**Then** 回 403
4. **Given** 清單被刪除，**When** 刪除完成，**Then** 其排程一併刪除

### User Story 3 - 一覽所有排程 (Priority: P2)

使用者可以在一個頁面看到所有清單的排程、下次執行時間與上次結果，快速確認夜間排程有沒有設好、有沒有失敗。

### Edge Cases

- **後端停機錯過排程時間**：重啟後不補跑錯過的每一次；若有錯過，最多只補跑一次，再從現在往後計算下次時間（見 Decisions）。
- **前一次還沒跑完**：同一個排程上一次的執行仍是 `pending` 或 `running` 時，這次不再排入，記錄為「略過（前一次仍在執行）」，避免夜間佇列越積越多。
- **清單是空的**：與手動執行相同，直接產生一筆 `completed`、0 個案例的記錄。
- **時區**：排程時間以設定的時區（預設 `Asia/Taipei`）解讀，不受容器時區（UTC）影響；台灣沒有日光節約時間，但計算邏輯仍以時區函式庫處理。
- **修改排程頻率**：儲存後下次執行時間立即依新頻率從現在重算。
- **排程器本身例外**：單一排程處理失敗只記錄 log，不影響其他排程與下一輪檢查。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系統 MUST 讓 editor 以上替清單建立排程，欄位含名稱、頻率、平行設定（`parallel_mode`、`max_workers`，與手動執行相同）、啟用狀態
- **FR-002**: 頻率 MUST 支援三種：每天固定時間（HH:MM）、每週指定星期與時間、每隔 N 分鐘（N ≥ 15）
- **FR-003**: 系統 MUST 在後端行程內以背景 task 每 30 秒檢查到期的排程，到期時透過既有的清單執行流程排入佇列（`pending`），不直接執行
- **FR-004**: 每個排程 MUST 保存 `next_run_at`，觸發時先以條件式 UPDATE 推進到下一次時間，確保同一次不會觸發兩次
- **FR-005**: 同一排程上一次的執行仍為 `pending` / `running` 時 MUST 略過本次，並記錄略過原因
- **FR-006**: 後端重啟後 MUST 接續排程；錯過的時間最多補跑一次
- **FR-007**: 排程產生的執行記錄 MUST 帶 `schedule_id`，前端在執行頁、結果頁與清單的執行歷史顯示「排程觸發」與排程名稱
- **FR-008**: 系統 MUST 提供排程 CRUD API 與啟用/停用；viewer 只能讀取
- **FR-009**: 排程列表 MUST 顯示下次執行時間、上次觸發時間、上次執行狀態（或略過原因）
- **FR-010**: 排程時間 MUST 以 `SCHEDULE_TIMEZONE`（預設 `Asia/Taipei`）解讀，DB 內一律存 UTC
- **FR-011**: 刪除清單時 MUST 一併刪除其排程；已產生的執行記錄保留

### Key Entities

- **ExecutionSchedule**（新）：`checklist_id`、`name`、`enabled`、`frequency`（`daily` / `weekly` / `interval`）、`time_of_day`、`weekdays`、`interval_minutes`、`parallel_mode`、`max_workers`、`next_run_at`、`last_triggered_at`、`last_execution_id`、`last_skip_reason`、`created_by`
- **ExecutionRecord**（既有，擴充）：新增 `schedule_id`（nullable）

## Success Criteria *(mandatory)*

- **SC-001**: 排程在到期後 60 秒內排入佇列
- **SC-002**: 後端在排程時間前後重啟，同一個排程時間不會產生兩筆執行
- **SC-003**: 一週內「每天 02:00」排程產生剛好 7 筆執行（期間無停機）
- **SC-004**: 既有後端與前端測試全部通過；沒有排程時，系統行為與現在相同

## Out of Scope

- 單一案例（試跑）的排程：排程只針對清單
- 執行失敗的通知（Email / Slack / LINE / webhook）：另案，會讀取排程執行的結果
- 外部 webhook / CI 觸發 API：另案
- 任意 cron 運算式（除非 Decisions 第 1 點選擇支援）
- 多個 uvicorn worker / 多台機器：與 spec 003 相同，維持單一行程
- 排程的執行歷史頁：沿用清單既有的執行歷史，以 `schedule_id` 篩選

## Decisions（待確認）

1. **頻率格式**：建議提供「每天 / 每週 / 每隔 N 分鐘」三種選單，不需要學 cron，也不新增套件；
   另一選項是直接輸入 cron 運算式（彈性最大，需新增 `croniter` 類套件、UI 較不友善）。
2. **錯過的排程**：建議重啟後最多補跑一次（例如 02:00 停機、03:00 重啟，會立刻補跑一次，之後回到每天 02:00）。
3. **前一次未完成**：建議略過本次並在排程列表顯示原因。
4. **時區**：建議全系統一個設定 `SCHEDULE_TIMEZONE=Asia/Taipei`，不做每個排程各自設定時區。
5. **排程執行的優先度**：建議與手動清單執行相同（0），試跑仍最優先。
