"""spec 004：排程到期時排入佇列、防重複、略過、補跑一次、停用與錯誤隔離。"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.core.database as core_db
import src.scheduling.runner as runner_module
from src.models.base import Base
from src.models.execution_record import ExecutionRecord
from src.models.execution_schedule import ExecutionSchedule
from src.models.test_checklist import TestChecklist as Checklist
from src.scheduling.runner import SKIP_PREVIOUS_ACTIVE, fire_schedule, tick
from src.scheduling.timing import as_utc

# 台北 2026-10-25 10:00
NOW = datetime(2026, 10, 25, 2, 0, tzinfo=timezone.utc)


@pytest.fixture
async def maker(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'schedule.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        await session.execute(text(
            "INSERT INTO test_cases (id, case_number, name, main_steps, created_by, version, is_deleted)"
            " VALUES ('case-1', 'TC-001', 'c', '', 'u', 1, 0)"
        ))
        await session.execute(text("INSERT INTO test_checklists (id, name, created_by) VALUES ('cl-1', 'cl', 'u')"))
        await session.execute(text("INSERT INTO test_checklists (id, name, created_by) VALUES ('cl-empty', 'e', 'u')"))
        await session.execute(text(
            "INSERT INTO checklist_items (id, checklist_id, test_case_id, position)"
            " VALUES ('item-1', 'cl-1', 'case-1', 1)"
        ))
        await session.commit()
    monkeypatch.setattr(core_db, "AsyncSessionLocal", maker)
    yield maker
    await engine.dispose()


async def _add_schedule(maker, schedule_id="s-1", checklist_id="cl-1", next_run_at=NOW, **kwargs) -> None:
    values = dict(
        id=schedule_id,
        checklist_id=checklist_id,
        name="nightly",
        enabled=True,
        frequency="daily",
        time_of_day="10:00",
        parallel_mode=True,
        max_workers=2,
        next_run_at=next_run_at,
        created_by="admin",
    )
    values.update(kwargs)
    async with maker() as session:
        session.add(ExecutionSchedule(**values))
        await session.commit()


async def _schedule(maker, schedule_id="s-1") -> ExecutionSchedule:
    async with maker() as session:
        return await session.get(ExecutionSchedule, schedule_id)


async def _records(maker) -> list[ExecutionRecord]:
    async with maker() as session:
        return list((await session.execute(select(ExecutionRecord))).scalars().all())


class TestTick:
    async def test_due_schedule_queues_pending_execution(self, maker):
        await _add_schedule(maker)

        queued = await tick(NOW)

        records = await _records(maker)
        assert [r.id for r in records] == queued
        record = records[0]
        assert record.status == "pending"
        assert record.checklist_id == "cl-1"
        assert record.schedule_id == "s-1"
        assert record.parallel_mode is True
        assert record.params == {"case_ids": ["case-1"], "concurrency": 2}

        schedule = await _schedule(maker)
        assert schedule.last_execution_id == record.id
        assert as_utc(schedule.last_triggered_at) == NOW
        # 台北 10:00 已觸發 → 明天台北 10:00
        assert as_utc(schedule.next_run_at) == NOW + timedelta(days=1)
        assert schedule.last_skip_reason is None

    async def test_not_due_and_disabled_are_ignored(self, maker):
        await _add_schedule(maker, "future", next_run_at=NOW + timedelta(seconds=1))
        await _add_schedule(maker, "off", enabled=False)

        assert await tick(NOW) == []
        assert await _records(maker) == []

    async def test_same_time_fires_only_once(self, maker):
        await _add_schedule(maker)

        assert len(await tick(NOW)) == 1
        assert await tick(NOW) == []
        assert len(await _records(maker)) == 1

    async def test_stale_next_run_at_is_not_fired_twice(self, maker, monkeypatch):
        """讀取排程之後、推進之前，另一輪已推進 next_run_at：條件式 UPDATE 不成立，不排入。"""
        await _add_schedule(maker)
        original_get = AsyncSession.get

        async def get_then_advance(session, entity, ident, **kwargs):
            obj = await original_get(session, entity, ident, **kwargs)
            if entity is ExecutionSchedule:
                async with maker() as other:
                    (await original_get(other, ExecutionSchedule, ident)).next_run_at = NOW + timedelta(days=1)
                    await other.commit()
            return obj

        monkeypatch.setattr(AsyncSession, "get", get_then_advance)

        assert await fire_schedule("s-1", NOW) is None
        assert await _records(maker) == []

    async def test_missed_runs_fire_once_and_resume_from_now(self, maker):
        # 停機三天：只補跑一次，下次時間從現在往後算
        await _add_schedule(maker, next_run_at=NOW - timedelta(days=3))

        assert len(await tick(NOW + timedelta(minutes=5))) == 1
        assert as_utc((await _schedule(maker)).next_run_at) == NOW + timedelta(days=1)
        assert len(await _records(maker)) == 1

    async def test_skips_when_previous_run_still_active(self, maker):
        await _add_schedule(maker, frequency="interval", time_of_day=None, interval_minutes=15)
        first = (await tick(NOW))[0]

        # 上一次仍是 pending → 略過並記原因
        assert await tick(NOW + timedelta(minutes=15)) == []
        schedule = await _schedule(maker)
        assert schedule.last_skip_reason == SKIP_PREVIOUS_ACTIVE
        assert schedule.last_execution_id == first
        assert as_utc(schedule.next_run_at) == NOW + timedelta(minutes=30)

        # 上一次結束後恢復觸發，並清除略過原因
        async with maker() as session:
            (await session.get(ExecutionRecord, first)).status = "completed"
            await session.commit()
        second = await tick(NOW + timedelta(minutes=30))
        assert len(second) == 1 and second[0] != first
        assert (await _schedule(maker)).last_skip_reason is None

    async def test_empty_checklist_completes_immediately(self, maker):
        await _add_schedule(maker, checklist_id="cl-empty")

        execution_id = (await tick(NOW))[0]

        async with maker() as session:
            record = await session.get(ExecutionRecord, execution_id)
        assert record.status == "completed"
        assert record.schedule_id == "s-1"

    async def test_one_failing_schedule_does_not_block_others(self, maker, monkeypatch):
        await _add_schedule(maker, "bad", next_run_at=NOW - timedelta(minutes=1))
        await _add_schedule(maker, "good")
        original = runner_module.fire_schedule

        async def flaky(schedule_id, now):
            if schedule_id == "bad":
                raise RuntimeError("boom")
            return await original(schedule_id, now)

        monkeypatch.setattr(runner_module, "fire_schedule", flaky)

        queued = await tick(NOW)

        assert len(queued) == 1
        assert (await _records(maker))[0].schedule_id == "good"


async def test_deleting_checklist_deletes_its_schedules(maker):
    await _add_schedule(maker)
    async with maker() as session:
        checklist = await session.get(Checklist, "cl-1")
        await session.delete(checklist)
        await session.commit()
    assert await _schedule(maker) is None
