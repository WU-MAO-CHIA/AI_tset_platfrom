from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


class DBConnectionService:
    """Manages connections to external databases (SQLite only in MVP).
    Uses its own isolated engine, separate from the app's async engine.
    """

    async def test_connection(self, connection_string: str) -> dict[str, Any]:
        if not connection_string:
            return {"success": False, "error": "connection_string is empty"}
        try:
            engine = create_engine(connection_string, connect_args={"timeout": 5})
            with engine.begin() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            return {"success": True, "error": None}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def execute_query(self, connection_string: str, sql: str, timeout: int = 10) -> dict[str, Any]:
        if not connection_string:
            raise ValueError("query_error: connection_string is empty")
        try:
            engine = create_engine(connection_string, connect_args={"timeout": timeout})
            with engine.begin() as conn:
                result = conn.execute(text(sql))
                if result.returns_rows:
                    columns = list(result.keys())
                    rows = [dict(zip(columns, row)) for row in result.fetchall()]
                else:
                    columns = []
                    rows = []
            engine.dispose()
            return {"columns": columns, "rows": rows}
        except SQLAlchemyError as exc:
            raise ValueError(f"query_error: {exc}") from exc
        except Exception as exc:
            raise ValueError(f"query_error: {exc}") from exc
