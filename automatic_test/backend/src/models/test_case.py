import uuid
from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class TestCase(Base, TimestampMixin):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    precondition_steps: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    main_steps: Mapped[str] = mapped_column(Text, nullable=False)
    system_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    modified_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    test_data: Mapped[list["TestData"]] = relationship("TestData", back_populates="test_case", cascade="all, delete-orphan")
    attachments: Mapped[list["MediaAttachment"]] = relationship("MediaAttachment", back_populates="test_case", cascade="all, delete-orphan")
    chat_messages: Mapped[list["CaseChatMessage"]] = relationship("CaseChatMessage", back_populates="test_case", cascade="all, delete-orphan", order_by="CaseChatMessage.created_at")  # type: ignore[name-defined]
    robot_script: Mapped[Optional["RobotScript"]] = relationship("RobotScript", back_populates="test_case", uselist=False, cascade="all, delete-orphan")  # type: ignore[name-defined]
