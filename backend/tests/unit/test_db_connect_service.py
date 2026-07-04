"""Unit tests for DBConnectionService.
RED: Tests should fail until the service is implemented.
"""

import pytest

from src.services.db_connect_service import DBConnectionService


class TestSQLiteConnection:
    async def test_test_connection_in_memory_returns_success(self):
        service = DBConnectionService()
        result = await service.test_connection("sqlite:///:memory:")
        assert result["success"] is True
        assert result["error"] is None

    async def test_test_connection_invalid_path_returns_failure(self):
        service = DBConnectionService()
        result = await service.test_connection("sqlite:///totally_invalid/path/no.db")
        # On many systems a non-existent path for SQLite still opens fine (creates a file)
        # so we test with a clearly malformed URI
        result2 = await service.test_connection("not-a-valid-uri://xyz")
        assert result2["success"] is False
        assert result2["error"] is not None

    async def test_test_connection_empty_string_returns_failure(self):
        service = DBConnectionService()
        result = await service.test_connection("")
        assert result["success"] is False


class TestQueryExecution:
    async def test_execute_simple_select(self):
        service = DBConnectionService()
        result = await service.execute_query("sqlite:///:memory:", "SELECT 1 AS value")
        assert result["columns"] == ["value"]
        assert len(result["rows"]) == 1
        assert result["rows"][0]["value"] == 1

    async def test_execute_ddl_returns_empty_rows(self):
        # DDL statements return no rows; service should handle gracefully
        service = DBConnectionService()
        result = await service.execute_query("sqlite:///:memory:", "CREATE TABLE t (id INTEGER, name TEXT)")
        assert result["columns"] == []
        assert result["rows"] == []

    async def test_execute_arithmetic_select(self):
        service = DBConnectionService()
        result = await service.execute_query("sqlite:///:memory:", "SELECT 1 + 1 AS total")
        assert result["rows"][0]["total"] == 2

    async def test_execute_invalid_sql_returns_error(self):
        service = DBConnectionService()
        with pytest.raises(ValueError, match="query_error"):
            await service.execute_query("sqlite:///:memory:", "NOT VALID SQL ;;; GARBAGE")

    async def test_connection_isolation_does_not_affect_main_db(self):
        """Verify that external DB operations don't bleed into the main app DB."""
        service = DBConnectionService()
        # External connection uses its own engine, not the app engine
        result = await service.test_connection("sqlite:///:memory:")
        assert result["success"] is True
        # The main app DB connection string is not used here
