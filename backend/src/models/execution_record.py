import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .test_checklist import TestChecklist
    from .test_case import TestCase


class ExecutionRecord(Base, TimestampMixin):
    """Records a single execution — either triggered from a checklist or a trial run on a single case.
    Exactly one of checklist_id or source_case_id must be non-null (enforced by CHECK constraint).
    """

    __tablename__ = "execution_records"
    __table_args__ = (
        CheckConstraint(
            "(checklist_id IS NOT NULL AND source_case_id IS NULL) OR "
            "(checklist_id IS NULL AND source_case_id IS NOT NULL)",
            name="ck_execution_has_one_source",
        ),
        # worker 取下一筆：WHERE status='pending' ORDER BY priority DESC, queued_at
        Index("ix_execution_records_queue", "status", "priority", "queued_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    checklist_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("test_checklists.id"), nullable=True, index=True
    )
    source_case_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("test_cases.id"), nullable=True, index=True
    )

    execution_type: Mapped[str] = mapped_column(String(20), nullable=False, default="checklist")
    # pending → running → completed / failed / error；重啟時 running → interrupted；排隊中取消 → cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    parallel_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_workers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    passed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 佇列（spec 003）：觸發當下的執行參數快照、優先度（試跑優先）、排隊時間、worker 心跳
    params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # 由排程觸發時記錄排程 ID（spec 004）；不設 FK，排程刪除後執行記錄照常保留
    schedule_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    checklist: Mapped[Optional["TestChecklist"]] = relationship("TestChecklist", back_populates="executions")
    source_case: Mapped[Optional["TestCase"]] = relationship("TestCase")
