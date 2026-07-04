"""RF Listener Plugin for pabot execution progress tracking.

Registered via: pabot --listener src/execution/listener.py:ExecutionListener:{execution_id}
Events are written to an asyncio.Queue which the FastAPI SSE endpoint reads from.
"""

import asyncio

_queues: dict[str, asyncio.Queue] = {}


def get_execution_queue(execution_id: str) -> asyncio.Queue:
    if execution_id not in _queues:
        _queues[execution_id] = asyncio.Queue()
    return _queues[execution_id]


def clear_execution_queue(execution_id: str) -> None:
    _queues.pop(execution_id, None)


class ExecutionListener:
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        self._queue = get_execution_queue(execution_id)

    def start_test(self, name: str, attrs: dict) -> None:
        self._queue.put_nowait({
            "event": "case_started",
            "execution_id": self.execution_id,
            "case_name": name,
        })

    def end_test(self, name: str, attrs: dict) -> None:
        self._queue.put_nowait({
            "event": "case_completed",
            "execution_id": self.execution_id,
            "case_name": name,
            "status": attrs.get("status", "FAIL"),
            "elapsed_ms": int(attrs.get("elapsedtime", 0)),
            "message": attrs.get("message", ""),
        })
