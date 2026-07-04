"""Unit tests for ExecutionListener RF Plugin and Queue Registry.
TDD RED: Tests should pass once src/execution/listener.py is implemented.
"""

import asyncio
import pytest


class TestQueueRegistry:
    def test_get_execution_queue_creates_new_queue(self):
        from src.execution.listener import get_execution_queue
        q = get_execution_queue("exec-001")
        assert isinstance(q, asyncio.Queue)

    def test_get_execution_queue_returns_same_queue_for_same_id(self):
        from src.execution.listener import get_execution_queue
        q1 = get_execution_queue("exec-same-id")
        q2 = get_execution_queue("exec-same-id")
        assert q1 is q2

    def test_get_execution_queue_returns_different_queues_for_different_ids(self):
        from src.execution.listener import get_execution_queue
        q1 = get_execution_queue("exec-aaa")
        q2 = get_execution_queue("exec-bbb")
        assert q1 is not q2


class TestExecutionListenerStartTest:
    def test_start_test_puts_case_started_event(self):
        from src.execution.listener import ExecutionListener, get_execution_queue
        execution_id = "exec-start-test-001"
        listener = ExecutionListener(execution_id)
        listener.start_test("登入功能測試", {"id": "tc-001", "starttime": "20260620 10:00:00.000"})

        queue = get_execution_queue(execution_id)
        assert not queue.empty()
        event = queue.get_nowait()
        assert event["event"] == "case_started"
        assert event["execution_id"] == execution_id
        assert event["case_name"] == "登入功能測試"

    def test_start_test_event_has_required_fields(self):
        from src.execution.listener import ExecutionListener, get_execution_queue
        execution_id = "exec-start-fields-001"
        listener = ExecutionListener(execution_id)
        listener.start_test("Test Name", {"id": "tc-002", "starttime": "20260620 10:00:00.000"})

        queue = get_execution_queue(execution_id)
        event = queue.get_nowait()
        assert "event" in event
        assert "execution_id" in event
        assert "case_name" in event


class TestExecutionListenerEndTest:
    def test_end_test_puts_case_completed_event_on_pass(self):
        from src.execution.listener import ExecutionListener, get_execution_queue
        execution_id = "exec-end-pass-001"
        listener = ExecutionListener(execution_id)
        listener.end_test("登入測試", {
            "id": "tc-001",
            "status": "PASS",
            "elapsedtime": 3200,
            "message": "",
        })

        queue = get_execution_queue(execution_id)
        assert not queue.empty()
        event = queue.get_nowait()
        assert event["event"] == "case_completed"
        assert event["execution_id"] == execution_id
        assert event["case_name"] == "登入測試"
        assert event["status"] == "PASS"
        assert event["elapsed_ms"] == 3200

    def test_end_test_puts_case_completed_event_on_fail(self):
        from src.execution.listener import ExecutionListener, get_execution_queue
        execution_id = "exec-end-fail-001"
        listener = ExecutionListener(execution_id)
        listener.end_test("失敗測試", {
            "id": "tc-002",
            "status": "FAIL",
            "elapsedtime": 1500,
            "message": "Element not found",
        })

        queue = get_execution_queue(execution_id)
        event = queue.get_nowait()
        assert event["status"] == "FAIL"
        assert event["elapsed_ms"] == 1500
        assert event["message"] == "Element not found"

    def test_end_test_event_has_required_fields(self):
        from src.execution.listener import ExecutionListener, get_execution_queue
        execution_id = "exec-end-fields-001"
        listener = ExecutionListener(execution_id)
        listener.end_test("Test", {
            "id": "tc-003",
            "status": "PASS",
            "elapsedtime": 100,
            "message": "",
        })

        queue = get_execution_queue(execution_id)
        event = queue.get_nowait()
        required = {"event", "execution_id", "case_name", "status", "elapsed_ms", "message"}
        assert required.issubset(set(event.keys()))

    def test_listener_api_version_is_2(self):
        from src.execution.listener import ExecutionListener
        assert ExecutionListener.ROBOT_LISTENER_API_VERSION == 2
