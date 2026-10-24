"""spec 003 第三階段：排入佇列、領取順序、同時執行上限與錯誤處理。"""

import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import src.core.database as core_db
import src.execution.worker as worker_module
from src.execution.events import fetch_events_after
from src.execution.worker import (
    PRIORITY_CHECKLIST,
    PRIORITY_TRIAL_RUN,
    ExecutionWorker,
    claim_next_pending,
    emit_queue_positions,
)
from src.models.base import Base
from src.models.execution_record import ExecutionRecord
from src.services.execution_service import ExecutionService

BASE_TIME = datetime(2026, 10, 24, 12, 0, 0)


@pytest.fixture
async def maker(monkeypatch, tmp_path):
    # worker 與測試會同時開 session；用 tmp_path 下的檔案 DB，讓每個 session
    # 各自一條連線（與正式環境相同），in-memory StaticPool 共用連線會互相 rollback
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'worker.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        await session.execute(text(
            "INSERT INTO test_cases (id, case_number, name, main_steps, created_by, version, is_deleted)"
            " VALUES ('case-1', 'TC-001', 'c', '', 'u', 1, 0)"
        ))
        await session.execute(text(
            "INSERT INTO test_checklists (id, name, created_by) VALUES ('cl-1', 'cl', 'u')"
        ))
        await session.execute(text(
            "INSERT INTO checklist_items (id, checklist_id, test_case_id, position)"
            " VALUES ('item-1', 'cl-1', 'case-1', 1)"
        ))
        await session.commit()
    monkeypatch.setattr(core_db, "AsyncSessionLocal", maker)
    yield maker
    await engine.dispose()


async def _add_pending(maker, execution_id: str, kind: str, minutes: int) -> None:
    async with maker() as session:
        session.add(ExecutionRecord(
            id=execution_id,
            checklist_id="cl-1" if kind == "checklist" else None,
            source_case_id="case-1" if kind == "trial_run" else None,
            execution_type=kind,
            status="pending",
            priority=PRIORITY_TRIAL_RUN if kind == "trial_run" else PRIORITY_CHECKLIST,
            queued_at=BASE_TIME + timedelta(minutes=minutes),
            params={"case_ids": ["case-1"], "concurrency": 1} if kind == "checklist" else {"rf_code": "x"},
            total_count=1,
        ))
        await session.commit()


async def _status(maker, execution_id: str) -> str:
    async with maker() as session:
        return (await session.get(ExecutionRecord, execution_id)).status


class TestClaim:
    async def test_trial_runs_first_then_oldest(self, maker):
        await _add_pending(maker, "cl-old", "checklist", 0)
        await _add_pending(maker, "cl-new", "checklist", 5)
        await _add_pending(maker, "trial", "trial_run", 10)

        order = [(await claim_next_pending()).id for _ in range(3)]

        assert order == ["trial", "cl-old", "cl-new"]
        assert await claim_next_pending() is None

    async def test_claim_marks_running_with_timestamps(self, maker):
        await _add_pending(maker, "cl-old", "checklist", 0)

        record = await claim_next_pending()

        assert record.status == "running"
        assert record.started_at is not None and record.heartbeat_at is not None
        assert await _status(maker, "cl-old") == "running"

    async def test_ignores_non_pending(self, maker):
        await _add_pending(maker, "cl-old", "checklist", 0)
        async with maker() as session:
            await session.execute(text("UPDATE execution_records SET status='cancelled'"))
            await session.commit()

        assert await claim_next_pending() is None


class TestQueuePositions:
    async def test_writes_ahead_count_per_pending_execution(self, maker):
        await _add_pending(maker, "cl-old", "checklist", 0)
        await _add_pending(maker, "trial", "trial_run", 10)

        await emit_queue_positions()

        async with maker() as session:
            trial = await fetch_events_after(session, "trial", 0)
            cl_old = await fetch_events_after(session, "cl-old", 0)
        assert [e.payload["ahead"] for e in trial] == [0]
        assert [e.payload["ahead"] for e in cl_old] == [1]
        assert trial[0].event == "execution_queued"


class TestEnqueue:
    async def test_trial_run_is_queued_with_params_and_priority(self, maker, monkeypatch):
        notified = []
        monkeypatch.setattr(worker_module, "_worker", ExecutionWorker(1))
        monkeypatch.setattr(worker_module._worker, "notify", lambda: notified.append(True))

        async with maker() as session:
            record = await ExecutionService(session).run_trial("case-1", rf_code="*** Test ***", case_name="n")

        async with maker() as session:
            stored = await session.get(ExecutionRecord, record.id)
            events = await fetch_events_after(session, record.id, 0)
        assert stored.status == "pending"
        assert stored.priority == PRIORITY_TRIAL_RUN
        assert stored.params == {"rf_code": "*** Test ***", "case_name": "n"}
        assert stored.queued_at is not None and stored.total_count == 1
        assert [e.event for e in events] == ["execution_queued"]
        assert notified == [True]

    async def test_checklist_is_queued_with_case_snapshot(self, maker, monkeypatch):
        monkeypatch.setattr(worker_module, "_worker", ExecutionWorker(1))

        async with maker() as session:
            record = await ExecutionService(session).run_checklist_parallel("cl-1", parallel_mode=True, max_workers=3)

        async with maker() as session:
            stored = await session.get(ExecutionRecord, record.id)
        assert stored.status == "pending"
        assert stored.priority == PRIORITY_CHECKLIST
        assert stored.params == {"case_ids": ["case-1"], "concurrency": 3}


class TestWorkerLoop:
    async def _wait_until(self, predicate, timeout=3.0):
        deadline = asyncio.get_running_loop().time() + timeout
        while not await predicate():
            if asyncio.get_running_loop().time() > deadline:
                raise AssertionError("condition not reached")
            await asyncio.sleep(0.01)

    async def test_runs_one_at_a_time_and_finishes_all(self, maker, monkeypatch):
        await _add_pending(maker, "a", "checklist", 0)
        await _add_pending(maker, "b", "checklist", 1)
        running_now: set[str] = set()
        max_parallel = 0
        release = asyncio.Event()

        async def fake_run(record):
            nonlocal max_parallel
            running_now.add(record.id)
            max_parallel = max(max_parallel, len(running_now))
            await release.wait()
            async with maker() as session:
                await session.execute(
                    text("UPDATE execution_records SET status='completed' WHERE id=:id"), {"id": record.id}
                )
                await session.commit()
            running_now.discard(record.id)

        monkeypatch.setattr(worker_module, "run_execution", fake_run)
        worker = ExecutionWorker(max_concurrent=1)
        worker.start()
        try:
            async def first_running():
                return await _status(maker, "a") == "running"
            await self._wait_until(first_running)
            await asyncio.sleep(0.05)
            assert await _status(maker, "b") == "pending"  # 上限 1：第二筆仍在排隊

            release.set()

            async def both_done():
                return (await _status(maker, "a"), await _status(maker, "b")) == ("completed", "completed")
            await self._wait_until(both_done)
        finally:
            await worker.stop()
        assert max_parallel == 1

    async def test_failure_marks_error_and_continues(self, maker, monkeypatch):
        await _add_pending(maker, "boom", "checklist", 0)
        await _add_pending(maker, "ok", "checklist", 1)

        async def fake_run(record):
            if record.id == "boom":
                raise RuntimeError("robot crashed")
            async with maker() as session:
                await session.execute(text("UPDATE execution_records SET status='completed' WHERE id='ok'"))
                await session.commit()

        monkeypatch.setattr(worker_module, "run_execution", fake_run)
        worker = ExecutionWorker(max_concurrent=1)
        worker.start()
        try:
            async def ok_done():
                return await _status(maker, "ok") == "completed"
            await self._wait_until(ok_done)
        finally:
            await worker.stop()

        assert await _status(maker, "boom") == "error"
        async with maker() as session:
            events = await fetch_events_after(session, "boom", 0)
        assert events[-1].event == "execution_error"
        assert events[-1].payload["__done__"] is True
        assert "robot crashed" in events[-1].payload["message"]

    async def test_notify_wakes_idle_worker(self, maker, monkeypatch):
        started = asyncio.Event()

        async def fake_run(record):
            started.set()

        monkeypatch.setattr(worker_module, "run_execution", fake_run)
        monkeypatch.setattr(worker_module, "_IDLE_POLL_SEC", 60.0)  # 不靠輪詢
        worker = ExecutionWorker(max_concurrent=1)
        worker.start()
        try:
            await asyncio.sleep(0.05)  # worker 已閒置等待
            await _add_pending(maker, "late", "trial_run", 0)
            worker.notify()
            await asyncio.wait_for(started.wait(), timeout=2)
        finally:
            await worker.stop()


class TestRunExecutionDispatch:
    async def test_dispatches_by_type_with_params(self, monkeypatch):
        calls = []

        async def fake_trial(execution_id, source_case_id, rf_code=None, case_name=None):
            calls.append(("trial", execution_id, source_case_id, rf_code, case_name))

        async def fake_checklist(execution_id, case_ids, max_workers):
            calls.append(("checklist", execution_id, case_ids, max_workers))

        monkeypatch.setattr(ExecutionService, "_execute_trial_bg", staticmethod(fake_trial))
        monkeypatch.setattr(ExecutionService, "_execute_all_cases_bg", staticmethod(fake_checklist))

        await worker_module.run_execution(ExecutionRecord(
            id="t", execution_type="trial_run", source_case_id="case-1",
            params={"rf_code": "x", "case_name": "n"},
        ))
        await worker_module.run_execution(ExecutionRecord(
            id="c", execution_type="checklist", checklist_id="cl-1",
            params={"case_ids": ["case-1", "case-2"], "concurrency": 2},
        ))

        assert calls == [
            ("trial", "t", "case-1", "x", "n"),
            ("checklist", "c", ["case-1", "case-2"], 2),
        ]
