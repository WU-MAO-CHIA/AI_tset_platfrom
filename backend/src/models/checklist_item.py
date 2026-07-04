import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .test_checklist import TestChecklist
    from .test_case import TestCase


class ChecklistItem(Base, TimestampMixin):
    __tablename__ = "checklist_items"
    __table_args__ = (UniqueConstraint("checklist_id", "test_case_id", name="uq_checklist_case"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    checklist_id: Mapped[str] = mapped_column(String(36), ForeignKey("test_checklists.id"), nullable=False)
    test_case_id: Mapped[str] = mapped_column(String(36), ForeignKey("test_cases.id"), nullable=False)
    position: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actual_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    checklist: Mapped["TestChecklist"] = relationship("TestChecklist", back_populates="items")
    test_case: Mapped["TestCase"] = relationship("TestCase")
