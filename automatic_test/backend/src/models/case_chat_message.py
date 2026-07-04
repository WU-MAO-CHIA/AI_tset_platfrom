import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ChatMessageType(str, Enum):
    """Phase 27: Message type enumeration."""
    CHAT = "chat"
    TRIAL_RUN_RESULT = "trial_run_result"


class CaseChatMessage(Base):
    __tablename__ = "case_chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    type: Mapped[ChatMessageType] = mapped_column(SQLEnum(ChatMessageType), nullable=False, default=ChatMessageType.CHAT)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    test_case: Mapped["TestCase"] = relationship("TestCase", back_populates="chat_messages")  # type: ignore[name-defined]
