from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings

settings = get_settings()


def enable_sqlite_wal(engine: AsyncEngine) -> None:
    """SQLite 每條連線開 WAL：API、執行 worker、排程與 SSE 輪詢可同時讀寫，減少 database is locked。"""
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # in-memory DB 會維持 memory，無妨
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")  # WAL 下 NORMAL 不會損毀資料庫
        cursor.close()


engine = create_async_engine(settings.database_url, echo=False)
enable_sqlite_wal(engine)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
