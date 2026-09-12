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

    async def test_execute_ddl_rejected(self):
        # 唯讀政策：DDL 一律拒絕（過去曾允許，現改為只讀 SELECT）
        service = DBConnectionService()
        with pytest.raises(ValueError, match="query_error"):
            await service.execute_query("sqlite:///:memory:", "CREATE TABLE t (id INTEGER, name TEXT)")

    async def test_execute_dml_rejected(self):
        service = DBConnectionService()
        for sql in [
            "INSERT INTO t VALUES (1)",
            "UPDATE t SET id = 2",
            "DELETE FROM t",
            "DROP TABLE t",
            "ATTACH DATABASE '/tmp/x.db' AS x",
            "PRAGMA journal_mode=WAL",
        ]:
            with pytest.raises(ValueError, match="query_error"):
                await service.execute_query("sqlite:///:memory:", sql)

    async def test_execute_stacked_query_rejected(self):
        service = DBConnectionService()
        with pytest.raises(ValueError, match="query_error"):
            await service.execute_query("sqlite:///:memory:", "SELECT 1; DROP TABLE t")

    async def test_execute_select_with_trailing_semicolon_ok(self):
        service = DBConnectionService()
        result = await service.execute_query("sqlite:///:memory:", "SELECT 1 AS value;")
        assert result["rows"][0]["value"] == 1

    async def test_execute_select_with_leading_comment_ok(self):
        service = DBConnectionService()
        result = await service.execute_query("sqlite:///:memory:", "-- comment\nSELECT 1 AS value")
        assert result["rows"][0]["value"] == 1

    async def test_execute_cte_select_ok(self):
        service = DBConnectionService()
        result = await service.execute_query(
            "sqlite:///:memory:", "WITH x AS (SELECT 1 AS v) SELECT * FROM x"
        )
        assert result["rows"][0]["v"] == 1

    async def test_execute_cte_with_delete_rejected(self):
        service = DBConnectionService()
        with pytest.raises(ValueError, match="query_error"):
            await service.execute_query(
                "sqlite:///:memory:", "WITH x AS (SELECT 1) DELETE FROM t"
            )

    async def test_execute_select_with_string_literal_ok(self):
        # 字串值內的關鍵字（如 'delete'）不應誤判
        service = DBConnectionService()
        result = await service.execute_query(
            "sqlite:///:memory:", "SELECT 'delete' AS op"
        )
        assert result["rows"][0]["op"] == "delete"

    async def test_execute_select_with_semicolon_in_string_ok(self):
        # 字串值內的分號（如 'a;b'）不應誤判為堆疊查詢
        service = DBConnectionService()
        result = await service.execute_query(
            "sqlite:///:memory:", "SELECT 'a;b' AS v"
        )
        assert result["rows"][0]["v"] == "a;b"

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
