# Server-Sent Events Contract: 執行進度串流

**Phase**: 1 | **Date**: 2026-05-19 | **Plan**: [plan.md](./plan.md)

## Endpoint

```
GET /api/v1/executions/{execution_id}/stream
Accept: text/event-stream
```

## Event Format

每個 SSE event 為 `data: {JSON}\n\n` 格式。

### Event: execution_started
```json
{
  "event": "execution_started",
  "execution_id": "uuid",
  "total_cases": 10,
  "parallel_mode": true,
  "max_workers": 5,
  "started_at": "2026-05-19T10:00:00Z"
}
```

### Event: case_started
```json
{
  "event": "case_started",
  "execution_id": "uuid",
  "case_result_id": "uuid",
  "case_number": "TC-003",
  "case_name": "登入功能測試",
  "position": 3
}
```

### Event: case_completed
```json
{
  "event": "case_completed",
  "execution_id": "uuid",
  "case_result_id": "uuid",
  "case_number": "TC-003",
  "status": "passed",
  "elapsed_ms": 3200,
  "failure_message": null
}
```

### Event: progress_update
每秒發送一次，提供整體進度摘要：
```json
{
  "event": "progress_update",
  "execution_id": "uuid",
  "status": "running",
  "total": 10,
  "completed": 4,
  "passed": 3,
  "failed": 1,
  "running_cases": ["TC-005", "TC-006"]
}
```

### Event: execution_completed
```json
{
  "event": "execution_completed",
  "execution_id": "uuid",
  "status": "completed",
  "total": 10,
  "passed": 9,
  "failed": 1,
  "elapsed_ms": 45000,
  "finished_at": "2026-05-19T10:00:45Z",
  "report_url": "/api/v1/executions/uuid/results"
}
```

### Event: execution_error
```json
{
  "event": "execution_error",
  "execution_id": "uuid",
  "error": "engine_unavailable",
  "message": "測試引擎無法啟動，請稍後重試"
}
```

## Client Reconnection

SSE 協定原生支援重連。每個 event 可攜帶 `id:` 欄位，讓客戶端在斷線重連後從該 ID 繼續接收。

```
id: evt_0042
data: {...}
```

## Termination

當 `execution_completed` 或 `execution_error` event 發送後，伺服器關閉串流。
客戶端在收到終止 event 後應主動關閉 EventSource。

## Frontend Example

```typescript
const evtSource = new EventSource(`/api/v1/executions/${executionId}/stream`)

evtSource.onmessage = (e) => {
  const event = JSON.parse(e.data)
  store.handleExecutionEvent(event)
  if (event.event === 'execution_completed' || event.event === 'execution_error') {
    evtSource.close()
  }
}

evtSource.onerror = () => {
  // EventSource 會自動重連，不需額外處理
}
```
