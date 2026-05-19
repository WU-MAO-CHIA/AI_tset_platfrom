import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class TestData(Base, TimestampMixin):
    __tablename__ = "test_data"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_case_id: Mapped[str] = mapped_column(String(36), ForeignKey("test_cases.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    field_value: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    import_source_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    row_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    test_case: Mapped["TestCase"] = relationship("TestCase", back_populates="test_data")
