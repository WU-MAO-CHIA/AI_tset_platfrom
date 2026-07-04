import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .checklist_item import ChecklistItem
    from .execution_record import ExecutionRecord


class TestChecklist(Base, TimestampMixin):
    __tablename__ = "test_checklists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    items: Mapped[list["ChecklistItem"]] = relationship(
        "ChecklistItem", back_populates="checklist", cascade="all, delete-orphan", order_by="ChecklistItem.position"
    )
    executions: Mapped[list["ExecutionRecord"]] = relationship(
        "ExecutionRecord", back_populates="checklist", cascade="all, delete-orphan"
    )
