"""RF Listener Plugin for pabot execution progress tracking.

Registered via: pabot --listener src/execution/listener.py:ExecutionListener:{execution_id}
Events are written to an asyncio.Queue which the FastAPI SSE endpoint reads from.
"""

import asyncio
import time
from typing import Optional

_queues: dict[str, asyncio.Queue] = {}
_queue_metadata: dict[str, dict] = {}
_MAX_QUEUE_SIZE = 1000
_QUEUE_TTL_SECONDS = 600
_cleanup_task: Optional[asyncio.Task] = None


async def _cleanup_queues() -> None:
    while True:
        await asyncio.sleep(60)
        now = time.time()
        to_remove = []
        for exec_id, meta in _queue_metadata.items():
            if now - meta.get("last_access", now) > _QUEUE_TTL_SECONDS:
                to_remove.append(exec_id)
        for exec_id in to_remove:
            _queues.pop(exec_id, None)
            _queue_metadata.pop(exec_id, None)


def _ensure_cleanup_task() -> None:
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_queues())


def get_execution_queue(execution_id: str) -> asyncio.Queue:
    _ensure_cleanup_task()
    if execution_id not in _queues:
        _queues[execution_id] = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
        _queue_metadata[execution_id] = {"created": time.time(), "last_access": time.time()}
    else:
        _queue_metadata[execution_id]["last_access"] = time.time()
    return _queues[execution_id]


def clear_execution_queue(execution_id: str) -> None:
    _queues.pop(execution_id, None)
    _queue_metadata.pop(execution_id, None)


def mark_queue_accessed(execution_id: str) -> None:
    if execution_id in _queue_metadata:
        _queue_metadata[execution_id]["last_access"] = time.time()


class ExecutionListener:
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        self._queue = get_execution_queue(execution_id)

    def start_test(self, name: str, attrs: dict) -> None:
        source = attrs.get("source", "")
        case_number = ""
        if source:
            import os
            case_number = os.path.splitext(os.path.basename(source))[0]
        self._queue.put_nowait({
            "event": "case_started",
            "execution_id": self.execution_id,
            "case_name": name,
            "case_number": case_number,
        })

    def end_test(self, name: str, attrs: dict) -> None:
        source = attrs.get("source", "")
        case_number = ""
        if source:
            import os
            case_number = os.path.splitext(os.path.basename(source))[0]
        self._queue.put_nowait({
            "event": "case_completed",
            "execution_id": self.execution_id,
            "case_name": name,
            "case_number": case_number,
            "status": attrs.get("status", "FAIL"),
            "elapsed_ms": int(attrs.get("elapsedtime", 0)),
            "message": attrs.get("message", ""),
        })
