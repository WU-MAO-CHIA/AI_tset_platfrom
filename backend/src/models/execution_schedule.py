import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .test_checklist import TestChecklist


class ExecutionSchedule(Base, TimestampMixin):
    """清單的排程（spec 004）：時間到時由 ScheduleRunner 排入執行佇列。

    時間欄位一律存 UTC；time_of_day / weekdays 依 SCHEDULE_TIMEZONE 解讀。
    """

    __tablename__ = "execution_schedules"
    __table_args__ = (
        # ScheduleRunner 每輪查詢：WHERE enabled AND next_run_at <= now
        Index("ix_execution_schedules_due", "enabled", "next_run_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    checklist_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_checklists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # daily（time_of_day）/ weekly（weekdays + time_of_day，0 = 週一）/ interval（interval_minutes）
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    time_of_day: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    weekdays: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    interval_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    parallel_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_workers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # 改用指定的執行環境（spec 005）；null = 依各案例的預設環境
    linux_environment_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    windows_environment_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # 停用時為 null
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_execution_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    last_skip_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    checklist: Mapped["TestChecklist"] = relationship("TestChecklist", back_populates="schedules")
