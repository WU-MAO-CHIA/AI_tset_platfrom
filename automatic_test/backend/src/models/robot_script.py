import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .test_case import TestCase


class RobotScript(Base, TimestampMixin):
    """Persisted Robot Framework script for a test case.

    One-to-one with TestCase. The file is also written to disk at
    robot_scripts/{case_number}.robot so the RF CLI can execute it;
    this table is the authoritative source that allows querying and
    auditing without touching the filesystem.
    """

    __tablename__ = "robot_scripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_cases.id"), nullable=False, unique=True, index=True
    )
    rf_code: Mapped[str] = mapped_column(Text, nullable=False)
    saved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    test_case: Mapped["TestCase"] = relationship("TestCase", back_populates="robot_script")
