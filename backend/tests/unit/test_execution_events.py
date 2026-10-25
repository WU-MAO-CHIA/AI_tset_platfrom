"""spec 003 第二階段：進度事件寫入 DB（EventSink）與背景執行送出的事件順序。"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import src.core.database as core_db
import src.services.execution_service as execution_service
from src.core.config import get_settings
from src.execution.events import EventSink, fetch_events_after
from src.models.base import Base
from src.models.execution_event import ExecutionEvent
from src.models.execution_record import ExecutionRecord
from src.services.execution_service import ExecutionService


@pytest.fixture
async def maker(monkeypatch, tmp_path):
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        for cid, num in [("case-1", "TC-001"), ("case-2", "TC-002")]:
            await session.execute(text(
                "INSERT INTO test_cases (id, case_number, name, main_steps, created_by, version, is_deleted)"
                f" VALUES ('{cid}', '{num}', 'c', '', 'u', 1, 0)"
            ))
        await session.execute(text(
            "INSERT INTO test_checklists (id, name, created_by) VALUES ('cl-1', 'cl', 'u')"
        ))
        await session.execute(text(
            "INSERT INTO execution_records (id, checklist_id, execution_type, status,"
            " parallel_mode, max_workers, passed_count, failed_count, total_count)"
            " VALUES ('exec-1', 'cl-1', 'checklist', 'running', 0, 1, 0, 0, 2)"
        ))
        await session.commit()

    monkeypatch.setattr(core_db, "AsyncSessionLocal", maker)
    monkeypatch.setattr(execution_service, "AsyncSessionLocal", maker)
    settings = get_settings()
    for attr in ("robot_scripts_dir", "execution_reports_dir"):
        monkeypatch.setattr(settings, attr, str(tmp_path / attr))
    yield maker
    await engine.dispose()


async def _events(maker) -> list[ExecutionEvent]:
    async with maker() as session:
        return await fetch_events_after(session, "exec-1", 0)


async def test_emit_writes_event_row(maker):
    await EventSink("exec-1").emit({"event": "case_started", "execution_id": "exec-1", "case_number": "TC-001"})

    events = await _events(maker)
    assert len(events) == 1
    assert events[0].event == "case_started"
    assert events[0].payload["case_number"] == "TC-001"


async def test_emit_failure_does_not_raise(monkeypatch):
    def broken_factory():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(core_db, "AsyncSessionLocal", broken_factory)
    await EventSink("exec-1").emit({"event": "case_started"})  # 不可中斷執行


async def test_fetch_events_after_returns_only_newer_in_order(maker):
    sink = EventSink("exec-1")
    for name in ("a", "b", "c"):
        await sink.emit({"event": name})
    first = (await _events(maker))[0]

    async with maker() as session:
        later = await fetch_events_after(session, "exec-1", first.id)
    assert [e.event for e in later] == ["b", "c"]


async def test_sequential_run_writes_events_and_final_status_first(maker, monkeypatch):
    seen_status_at_done: list[str] = []
    real_emit = EventSink.emit

    async def spying_emit(self, payload):
        if payload.get("__done__"):
            async with maker() as session:
                record = await session.get(ExecutionRecord, self.execution_id)
                seen_status_at_done.append(record.status)
        await real_emit(self, payload)

    async def fake_run(case_id, robot_code, timeout_sec, report_dest, target=None):
        return {"status": "passed" if case_id == "case-1" else "failed", "elapsed_ms": 5}

    monkeypatch.setattr(EventSink, "emit", spying_emit)
    monkeypatch.setattr(ExecutionService, "_run_single_case_with_timeout", staticmethod(fake_run))

    await ExecutionService._execute_all_cases_bg("exec-1", ["case-1", "case-2"], max_workers=1)

    events = await _events(maker)
    assert [e.event for e in events] == [
        "case_started", "case_completed", "case_started", "case_completed", "execution_completed",
    ]
    done = events[-1].payload
    assert done["__done__"] is True
    assert (done["status"], done["passed"], done["failed"]) == ("failed", 1, 1)
    # 結束事件送出時，最終狀態已寫入 DB（前端收到後重新查詢會拿到最終狀態）
    assert seen_status_at_done == ["failed"]
