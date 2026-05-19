import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class CaseResult(Base, TimestampMixin):
    __tablename__ = "case_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("execution_records.id"), nullable=False, index=True)
    test_case_id: Mapped[str] = mapped_column(String(36), ForeignKey("test_cases.id"), nullable=False, index=True)
    case_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    automation_code_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("automation_codes.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    elapsed_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    failure_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    media: Mapped[list["ExecutionMedia"]] = relationship(
        "ExecutionMedia", back_populates="case_result", cascade="all, delete-orphan", order_by="ExecutionMedia.step_index"
    )
