import uuid
from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin

# docker compose 內建的 runner 不存在這張表裡，以固定 id 代表（見 runner_environment_service）
BUILTIN_ENVIRONMENT_ID = "builtin-linux"

KIND_LINUX = "linux"
KIND_WINDOWS = "windows"
ENVIRONMENT_KINDS = (KIND_LINUX, KIND_WINDOWS)


class RunnerEnvironment(Base, TimestampMixin):
    """admin 登記的執行環境（spec 005）：一台 runner 的位址與 token。

    linux 環境執行網頁測試，windows 環境執行桌面應用程式測試。
    """

    __tablename__ = "runner_environments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    # Fernet 密文（src/core/secret_box.py），API 永不回傳
    token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
