"""排程管理（spec 004 第 2 階段）：建立、修改、刪除排程，並維護 next_run_at。"""

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.execution_record import ExecutionRecord
from src.models.execution_schedule import ExecutionSchedule
from src.models.test_checklist import TestChecklist
from src.scheduling.runner import next_run_for
from src.scheduling.timing import utcnow, validate_frequency

# 這些欄位變動時從現在重新計算下次執行時間；只改名稱等欄位不影響已排定的時間
_TIMING_FIELDS = ("enabled", "frequency", "time_of_day", "weekdays", "interval_minutes")


def _normalize(values: dict[str, Any]) -> dict[str, Any]:
    """只保留目前頻率用得到的欄位，避免殘留其他頻率的設定。"""
    frequency = values["frequency"]
    if frequency != "weekly":
        values["weekdays"] = None
    elif values.get("weekdays"):
        values["weekdays"] = sorted(set(values["weekdays"]))
    if frequency == "interval":
        values["time_of_day"] = None
    else:
        values["interval_minutes"] = None
    return values


def _validate(values: dict[str, Any]) -> None:
    from src.core.config import get_settings

    if not values.get("name", "").strip():
        raise ValueError("name must not be empty")
    validate_frequency(values["frequency"], values.get("time_of_day"), values.get("weekdays"), values.get("interval_minutes"))
    limit = get_settings().parallel_max_workers
    if not 1 <= values["max_workers"] <= limit:
        raise ValueError(f"max_workers must be between 1 and {limit}")


class ScheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, schedule_id: str) -> Optional[ExecutionSchedule]:
        return await self._session.get(ExecutionSchedule, schedule_id)

    async def list_schedules(self, checklist_id: Optional[str] = None) -> list[ExecutionSchedule]:
        query = select(ExecutionSchedule).order_by(ExecutionSchedule.created_at)
        if checklist_id is not None:
            query = query.where(ExecutionSchedule.checklist_id == checklist_id)
        return list((await self._session.execute(query)).scalars().all())

    async def create(self, checklist_id: str, created_by: str, **fields: Any) -> Optional[ExecutionSchedule]:
        if await self._session.get(TestChecklist, checklist_id) is None:
            return None
        values = _normalize(dict(fields))
        values["name"] = values["name"].strip()
        _validate(values)
        schedule = ExecutionSchedule(checklist_id=checklist_id, created_by=created_by, **values)
        schedule.next_run_at = next_run_for(schedule, utcnow())
        self._session.add(schedule)
        await self._session.flush()
        return schedule

    async def update(self, schedule_id: str, **fields: Any) -> Optional[ExecutionSchedule]:
        schedule = await self.get(schedule_id)
        if schedule is None:
            return None
        current = {
            key: getattr(schedule, key)
            for key in ("name", "enabled", "frequency", "time_of_day", "weekdays",
                        "interval_minutes", "parallel_mode", "max_workers")
        }
        values = _normalize({**current, **fields})
        values["name"] = values["name"].strip()
        _validate(values)
        timing_changed = any(values[key] != current[key] for key in _TIMING_FIELDS)
        for key, value in values.items():
            setattr(schedule, key, value)
        if timing_changed:
            schedule.next_run_at = next_run_for(schedule, utcnow())
            # 重新啟用或改頻率後，舊的略過原因已不適用
            schedule.last_skip_reason = None
        await self._session.flush()
        return schedule

    async def delete(self, schedule_id: str) -> bool:
        schedule = await self.get(schedule_id)
        if schedule is None:
            return False
        await self._session.delete(schedule)
        await self._session.flush()
        return True

    async def checklist_names(self, schedules: list[ExecutionSchedule]) -> dict[str, str]:
        ids = {s.checklist_id for s in schedules}
        if not ids:
            return {}
        result = await self._session.execute(
            select(TestChecklist.id, TestChecklist.name).where(TestChecklist.id.in_(ids))
        )
        return dict(result.all())

    async def last_execution_statuses(self, schedules: list[ExecutionSchedule]) -> dict[str, str]:
        ids = {s.last_execution_id for s in schedules if s.last_execution_id}
        if not ids:
            return {}
        result = await self._session.execute(
            select(ExecutionRecord.id, ExecutionRecord.status).where(ExecutionRecord.id.in_(ids))
        )
        return dict(result.all())

    async def names_by_id(self, schedule_ids: set[str]) -> dict[str, str]:
        """執行記錄顯示「排程：<名稱>」用；已刪除的排程不在結果中。"""
        schedule_ids = {i for i in schedule_ids if i}
        if not schedule_ids:
            return {}
        result = await self._session.execute(
            select(ExecutionSchedule.id, ExecutionSchedule.name).where(ExecutionSchedule.id.in_(schedule_ids))
        )
        return dict(result.all())
