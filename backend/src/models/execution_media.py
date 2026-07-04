import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class ExecutionMedia(Base, TimestampMixin):
    __tablename__ = "execution_media"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_result_id: Mapped[str] = mapped_column(String(36), ForeignKey("case_results.id"), nullable=False, index=True)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    step_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    step_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    case_result: Mapped["CaseResult"] = relationship("CaseResult", back_populates="media")
