# Feature Specification: 執行佇列持久化（DB 佇列）

**Feature Branch**: `003-persistent-execution-queue`
**Created**: 2026-10-24
**Status**: Approved
**Input**: 使用者選擇方案一：「執行佇列改為持久化（DB 佇列），重啟後可恢復或標記中斷」

## 背景

目前按下「執行」後，後端把 `execution_records.status` 設為 `running`，再以
`asyncio.create_task` 在同一個行程裡跑 robot / pabot；SSE 進度事件放在記憶體中的
`asyncio.Queue`（`src/execution/listener.py`）。因此：

- 後端重啟（改設定、重建容器、當機）時，執行中的工作直接消失，DB 記錄永遠停在 `running`。
- 進度事件只存在記憶體，重新整理頁面或重啟後就拿不回來。
- 沒有排隊與總量上限：同時觸發多次執行就同時開多組瀏覽器。
- 只能跑單一 uvicorn worker。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 執行會排隊，不會同時爆量 (Priority: P1)

測試人員連續觸發多個清單執行或試跑時，系統依序排隊，同時執行的數量不超過設定上限，
其餘顯示「排隊中」。

**Independent Test**: 把上限設為 1，連續觸發兩次清單執行，第二筆在第一筆結束前維持 `pending`。

**Acceptance Scenarios**:

1. **Given** 上限為 1 且已有一筆執行中，**When** 使用者再觸發一次執行，**Then** API 立即回 202，新記錄狀態為 `pending`，執行頁顯示「排隊中（前面還有 N 筆）」
2. **Given** 前一筆執行結束，**When** worker 取下一筆，**Then** 該筆狀態變為 `running`，頁面不需重新整理即更新
3. **Given** 有試跑與清單執行同時在排隊，**When** worker 取下一筆，**Then** 試跑優先（試跑是使用者在案例頁等待結果的互動操作）

### User Story 2 - 後端重啟不會留下「永遠執行中」的記錄 (Priority: P1)

後端重啟後，之前停在 `running` 的執行被標記為「已中斷」，`pending` 的執行在重啟後繼續排隊執行。

**Independent Test**: 在 DB 放一筆 `running`、一筆 `pending`，重新啟動 app，前者變為 `interrupted`，後者被執行。

**Acceptance Scenarios**:

1. **Given** 重啟前有一筆 `running` 的執行，**When** 後端啟動，**Then** 狀態改為 `interrupted`、寫入 `finished_at`，並追加一筆 `execution_interrupted` 事件
2. **Given** 重啟前有 `pending` 的執行，**When** 後端啟動，**Then** 依原本的排隊順序繼續執行
3. **Given** 執行已被標為 `interrupted`，**When** 使用者開啟結果頁，**Then** 顯示「執行因服務重啟而中斷」，已完成的案例結果照常顯示

### User Story 3 - 重新整理或重連後仍看得到完整進度 (Priority: P2)

執行進度事件寫入 DB，SSE 從 DB 讀取；重新整理頁面、網路斷線重連或後端重啟後，
前端可以從頭（或從上次收到的事件之後）補齊進度。

**Acceptance Scenarios**:

1. **Given** 執行進行到第 3 個案例，**When** 使用者重新整理執行頁，**Then** 前 3 個案例的開始/完成事件重新出現，之後的事件持續即時推送
2. **Given** EventSource 斷線重連並帶上 `Last-Event-ID`，**When** 重連成功，**Then** 只補送該 ID 之後的事件，不重複

### User Story 4 - 取消排隊中的執行 (Priority: P3)

使用者可以取消自己觸發、仍在 `pending` 的執行。

**Acceptance Scenarios**:

1. **Given** 一筆 `pending` 執行，**When** editor 以上的使用者按「取消」，**Then** 狀態變為 `cancelled`，不會被 worker 取走
2. **Given** 一筆 `running` 執行，**When** 使用者嘗試取消，**Then** 回 409（本功能不處理中止執行中的 robot 子程序）

### Edge Cases

- 清單在排隊期間被修改：執行內容以「觸發當下」的案例清單為準（觸發時存快照）。
- 試跑帶的 RF code 覆寫：觸發時一併存入記錄，worker 取用時不依賴原請求。
- 執行中 worker 本身拋例外：該筆標 `error`，worker 繼續處理下一筆，不會整個停住。
- `running` 卻沒有對應 worker（例如 worker task 意外結束）：啟動檢查會處理；執行中另由 worker 心跳判斷（見 plan）。
- SSE 訂閱一筆不存在或已刪除的執行：維持現有 404 行為。
- 多個 uvicorn worker：本功能不支援，仍維持單一 worker（見 Out of Scope）。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 觸發清單執行或試跑時，系統 MUST 只建立 `pending` 記錄並回 202，不在請求內啟動執行
- **FR-002**: 系統 MUST 在啟動時開啟一個背景 worker，依「試跑優先、再依建立時間」取出 `pending` 記錄執行
- **FR-003**: 同時執行的數量 MUST 不超過 `EXECUTION_MAX_CONCURRENT`（預設 1）；單一清單內的 pabot 平行度仍由既有的 `max_workers` / `PARALLEL_MAX_WORKERS` 控制
- **FR-004**: 觸發時 MUST 保存執行所需的參數快照（案例 ID 清單、平行設定、試跑的 RF code 覆寫、案例名稱）
- **FR-005**: 後端啟動時 MUST 將所有 `running` 記錄改為 `interrupted`，並保留已寫入的 `case_results`
- **FR-006**: 所有進度事件（`case_started`、`case_completed`、`pabot_started`、`execution_completed`、`execution_error` 等）MUST 依序寫入 DB，帶遞增序號
- **FR-007**: SSE 端點 MUST 從 DB 讀取事件推送，支援 `Last-Event-ID` 補送；事件格式與現有前端相容
- **FR-008**: 排隊中的執行 MUST 推送 `execution_queued` 事件，內容含前面還有幾筆
- **FR-009**: editor 以上 MUST 能取消 `pending` 執行（新狀態 `cancelled`）
- **FR-010**: 事件資料 MUST 隨既有的每日清理一併清除（保留 30 天，與 trial run 清理一致）
- **FR-011**: 前端執行頁與結果頁 MUST 能顯示 `pending`（排隊中）、`interrupted`（已中斷）、`cancelled`（已取消）三種新狀態

### Key Entities

- **ExecutionRecord**（既有，擴充）：新增狀態 `pending`（既有預設值，開始實際使用）、`interrupted`、`cancelled`；新增 `params`（JSON 快照）、`priority`、`queued_at`、`heartbeat_at`
- **ExecutionEvent**（新）：`execution_id`、`seq`（遞增）、`event`、`payload`（JSON）、`created_at`

## Success Criteria *(mandatory)*

- **SC-001**: 後端重啟後，DB 中不存在任何沒有 worker 在跑卻標為 `running` 的記錄
- **SC-002**: 上限 1 時連續觸發 5 次執行，任何時刻最多 1 筆為 `running`，5 筆最終都有結束狀態
- **SC-003**: 執行中重新整理頁面，進度在 2 秒內補齊且與重新整理前一致
- **SC-004**: 事件從寫入 DB 到前端收到的延遲中位數 ≤ 1.5 秒
- **SC-005**: 既有的後端與前端測試全部通過，前端在沒有新狀態的舊記錄上行為不變

## Out of Scope

- 多個 uvicorn worker 或多台機器分散執行（之後改 Redis/arq 時處理，本設計的資料表與狀態可沿用）
- 中止執行中的 robot 子程序
- 自動重跑被中斷的執行（使用者可手動重新觸發）
- 從 SQLite 換成 PostgreSQL（另案）
- 排程 / webhook 觸發（另案，會建立在這個佇列之上）

## Decisions

1. 同時執行上限預設值為 1（2026-10-24 確認）；機器資源足夠可在 `.env` 調高 `EXECUTION_MAX_CONCURRENT`。
   這是「同時跑幾筆執行（robot / pabot 子程序）」，仍只有一個 uvicorn 行程；單一清單內的 pabot 平行度另由 `max_workers` 控制。
2. 試跑優先於清單執行（2026-10-24 確認）。
