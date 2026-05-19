import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
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
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    checklist_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("test_checklists.id"), nullable=True, index=True
    )
    source_case_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("test_cases.id"), nullable=True, index=True
    )

    execution_type: Mapped[str] = mapped_column(String(20), nullable=False, default="checklist")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    parallel_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_workers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    passed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    checklist: Mapped[Optional["TestChecklist"]] = relationship("TestChecklist", back_populates="executions")
    source_case: Mapped[Optional["TestCase"]] = relationship("TestCase")
