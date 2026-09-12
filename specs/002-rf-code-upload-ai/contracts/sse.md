# SSE Events: RF Code Upload and AI Integration

**Feature**: RF Code Upload and AI Integration  
**Date**: 2026-09-10

## Overview

No new SSE events are introduced by this feature. Existing SSE events for test execution remain unchanged.

## Existing SSE Events (Unchanged)

### Execution Stream (`/executions/{execution_id}/stream`)

| Event | Description | Payload |
|-------|-------------|---------|
| `execution_started` | Execution begins | `{event, execution_id, status, total_cases}` |
| `case_started` | Test case begins | `{event, execution_id, case_id, case_number, case_name}` |
| `case_completed` | Test case finishes | `{event, execution_id, case_id, case_number, status, elapsed_ms, message}` |
| `pabot_started` | Parallel execution begins | `{event, execution_id, total, processes}` |
| `pabot_error` | Parallel execution error | `{event, execution_id, message}` |
| `execution_completed` | Execution finishes | `{event, execution_id, status, passed, failed, total, report_url, __done__: true}` |
| `execution_error` | Execution error | `{event, execution_id, message, __done__: true}` |

## AI Chat - No SSE

AI chat uses standard HTTP request/response, not SSE. The RF code context is sent in the request body and returned in the response.

## Future Consideration

If real-time AI streaming is added later, new SSE events would be:
- `ai_stream_start` - AI response begins
- `ai_stream_chunk` - Partial response chunk
- `ai_stream_complete` - AI response complete
- `ai_stream_error` - AI error

But this is out of scope for current feature.