"""排程器（spec 004）。

後端啟動時開啟，每 30 秒檢查到期的排程，到期時透過既有的清單執行流程排入
spec 003 的佇列（pending），由 ExecutionWorker 執行。不直接執行，也不需要額外服務。
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update

import src.core.database as core_db
from src.models.execution_record import ExecutionRecord
from src.models.execution_schedule import ExecutionSchedule
from src.scheduling.timing import compute_next_run, utcnow

logger = logging.getLogger(__name__)

_TICK_SEC = 30.0

SKIP_PREVIOUS_ACTIVE = "前一次執行仍在排隊或執行中"


def next_run_for(schedule: ExecutionSchedule, after: datetime) -> Optional[datetime]:
    """排程在 after 之後的下一次時間；停用時為 None。"""
    if not schedule.enabled:
        return None
    from src.core.config import get_settings
    return compute_next_run(
        schedule.frequency,
        schedule.time_of_day,
        schedule.weekdays,
        schedule.interval_minutes,
        after,
        get_settings().schedule_timezone,
    )


async def fire_schedule(schedule_id: str, now: datetime) -> Optional[str]:
    """觸發一個到期的排程，回傳排入的 execution_id；未觸發（已被處理、略過）時回傳 None。"""
    from src.services.execution_service import ExecutionService

    async with core_db.AsyncSessionLocal() as session:
        schedule = await session.get(ExecutionSchedule, schedule_id)
        if schedule is None or not schedule.enabled or schedule.next_run_at is None:
            return None

        # 先把 next_run_at 推進到 now 之後：條件式 UPDATE 確保同一次只觸發一次；
        # 停機錯過的多次時間也只會在這裡觸發一次
        claimed = await session.execute(
            update(ExecutionSchedule)
            .where(
                ExecutionSchedule.id == schedule_id,
                ExecutionSchedule.enabled.is_(True),
                ExecutionSchedule.next_run_at == schedule.next_run_at,
            )
            .values(next_run_at=next_run_for(schedule, now), last_triggered_at=now)
            .execution_options(synchronize_session=False)
        )
        if claimed.rowcount != 1:
            await session.rollback()
            return None

        if schedule.last_execution_id:
            previous = await session.get(ExecutionRecord, schedule.last_execution_id)
            if previous is not None and previous.status in ("pending", "running"):
                await session.execute(
                    update(ExecutionSchedule)
                    .where(ExecutionSchedule.id == schedule_id)
                    .values(last_skip_reason=SKIP_PREVIOUS_ACTIVE)
                    .execution_options(synchronize_session=False)
                )
                await session.commit()
                logger.info("Schedule %s skipped: previous execution %s still active", schedule_id, previous.id)
                return None

        record = await ExecutionService(session).run_checklist_parallel(
            schedule.checklist_id,
            parallel_mode=schedule.parallel_mode,
            max_workers=schedule.max_workers,
            schedule_id=schedule_id,
            linux_environment_id=schedule.linux_environment_id,
            windows_environment_id=schedule.windows_environment_id,
        )
        await session.execute(
            update(ExecutionSchedule)
            .where(ExecutionSchedule.id == schedule_id)
            .values(last_execution_id=record.id, last_skip_reason=None)
            .execution_options(synchronize_session=False)
        )
        await session.commit()
        logger.info("Schedule %s queued execution %s", schedule_id, record.id)
        return record.id


async def tick(now: Optional[datetime] = None) -> list[str]:
    """處理所有到期的排程，回傳本輪排入的 execution_id。單一排程失敗不影響其他排程。"""
    now = now or utcnow()
    async with core_db.AsyncSessionLocal() as session:
        result = await session.execute(
            select(ExecutionSchedule.id)
            .where(ExecutionSchedule.enabled.is_(True), ExecutionSchedule.next_run_at <= now)
            .order_by(ExecutionSchedule.next_run_at)
        )
        due = list(result.scalars().all())

    queued = []
    for schedule_id in due:
        try:
            execution_id = await fire_schedule(schedule_id, now)
        except Exception:
            logger.exception("Firing schedule %s failed", schedule_id)
            continue
        if execution_id:
            queued.append(execution_id)
    return queued


class ScheduleRunner:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        if not self.running:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def _loop(self) -> None:
        while True:
            try:
                await tick()
            except Exception:
                logger.exception("Schedule tick failed")
            await asyncio.sleep(_TICK_SEC)


_runner: Optional[ScheduleRunner] = None


def get_schedule_runner() -> ScheduleRunner:
    global _runner
    if _runner is None:
        _runner = ScheduleRunner()
    return _runner
