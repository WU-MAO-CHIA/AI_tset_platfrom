from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.database import enable_sqlite_wal


async def test_file_sqlite_connections_use_wal(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'wal.db'}")
    enable_sqlite_wal(engine)
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("PRAGMA journal_mode"))).scalar() == "wal"
            assert (await conn.execute(text("PRAGMA busy_timeout"))).scalar() == 5000
            assert (await conn.execute(text("PRAGMA synchronous"))).scalar() == 1  # NORMAL
    finally:
        await engine.dispose()
