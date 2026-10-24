"""spec 003 第一階段：啟動時把殘留的 running 執行標為 interrupted。"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import src.core.database as core_db
import src.main as main_module
from src.execution.recovery import TERMINAL_STATUSES, mark_interrupted_executions
from src.models.base import Base
from src.models.execution_event import ExecutionEvent
from src.models.execution_record import ExecutionRecord


@pytest.fixture
async def maker():
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        await session.execute(text(
            "INSERT INTO test_cases (id, case_number, name, main_steps, created_by, version, is_deleted)"
            " VALUES ('case-1', 'TC-001', 'c', '', 'u', 1, 0)"
        ))
        for exec_id, status in [
            ("run-1", "running"), ("run-2", "running"),
            ("pend-1", "pending"), ("done-1", "completed"),
        ]:
            await session.execute(text(
                "INSERT INTO execution_records (id, source_case_id, execution_type, status,"
                " parallel_mode, max_workers, passed_count, failed_count, total_count, priority)"
                f" VALUES ('{exec_id}', 'case-1', 'trial_run', '{status}', 0, 1, 0, 0, 1, 0)"
            ))
        await session.commit()
    yield maker
    await engine.dispose()


async def _statuses(maker) -> dict[str, str]:
    async with maker() as session:
        rows = await session.execute(select(ExecutionRecord.id, ExecutionRecord.status))
        return dict(rows.all())


async def test_running_becomes_interrupted_others_untouched(maker):
    async with maker() as session:
        count = await mark_interrupted_executions(session)

    assert count == 2
    assert await _statuses(maker) == {
        "run-1": "interrupted", "run-2": "interrupted",
        "pend-1": "pending", "done-1": "completed",
    }
    async with maker() as session:
        record = await session.get(ExecutionRecord, "run-1")
        assert record.finished_at is not None


async def test_writes_done_event_per_interrupted_execution(maker):
    async with maker() as session:
        await mark_interrupted_executions(session)
        events = (await session.execute(select(ExecutionEvent))).scalars().all()

    assert sorted(e.execution_id for e in events) == ["run-1", "run-2"]
    for e in events:
        assert e.event == "execution_interrupted"
        assert e.payload["status"] == "interrupted"
        assert e.payload["__done__"] is True


async def test_second_run_is_noop(maker):
    async with maker() as session:
        await mark_interrupted_executions(session)
    async with maker() as session:
        assert await mark_interrupted_executions(session) == 0


async def test_startup_hook_uses_session_factory(maker, monkeypatch):
    monkeypatch.setattr(core_db, "AsyncSessionLocal", maker)
    await main_module._recover_executions()
    assert (await _statuses(maker))["run-1"] == "interrupted"


async def test_startup_hook_swallows_errors(monkeypatch):
    def broken_factory():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(core_db, "AsyncSessionLocal", broken_factory)
    await main_module._recover_executions()  # 不可讓服務啟動失敗


def test_interrupted_is_terminal():
    assert "interrupted" in TERMINAL_STATUSES
    assert "running" not in TERMINAL_STATUSES and "pending" not in TERMINAL_STATUSES
