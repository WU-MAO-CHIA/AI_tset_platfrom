import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect them for autogenerate
from src.models.base import Base  # noqa: E402

# Model imports — register all models with Base.metadata
from src.models.test_case import TestCase  # noqa: E402, F401
from src.models.test_data import TestData  # noqa: E402, F401
from src.models.media_attachment import MediaAttachment  # noqa: E402, F401
from src.models.test_checklist import TestChecklist  # noqa: E402, F401
from src.models.checklist_item import ChecklistItem  # noqa: E402, F401
from src.models.execution_record import ExecutionRecord  # noqa: E402, F401
from src.models.db_connection import DBConnection  # noqa: E402, F401
from src.models.automation_code import AutomationCode  # noqa: E402, F401
from src.models.case_result import CaseResult  # noqa: E402, F401
from src.models.execution_media import ExecutionMedia  # noqa: E402, F401
from src.models.case_chat_message import CaseChatMessage  # noqa: E402, F401
from src.models.robot_script import RobotScript  # noqa: E402, F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
