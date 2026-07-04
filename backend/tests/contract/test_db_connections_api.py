"""Contract tests for /api/v1/db-connections endpoints.
RED: Tests should fail until the API is implemented.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class TestCreateDBConnection:
    async def test_create_connection_returns_201(self, client):
        r = await client.post("/api/v1/db-connections", json={
            "name": "Test SQLite DB",
            "connection_string": "sqlite:///./tests/fixtures/sample.db",
            "created_by": "tester",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Test SQLite DB"
        assert "id" in data

    async def test_create_connection_missing_name_returns_422(self, client):
        r = await client.post("/api/v1/db-connections", json={
            "connection_string": "sqlite:///./test.db",
            "created_by": "tester",
        })
        assert r.status_code == 422


class TestTestConnection:
    async def test_test_valid_sqlite_connection_returns_success(self, client):
        create_r = await client.post("/api/v1/db-connections", json={
            "name": "Valid SQLite",
            "connection_string": "sqlite:///:memory:",
            "created_by": "tester",
        })
        conn_id = create_r.json()["id"]

        r = await client.post(f"/api/v1/db-connections/{conn_id}/test")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    async def test_test_invalid_connection_returns_failure(self, client):
        create_r = await client.post("/api/v1/db-connections", json={
            "name": "Bad Connection",
            "connection_string": "sqlite:///nonexistent_dir/no.db",
            "created_by": "tester",
        })
        conn_id = create_r.json()["id"]

        r = await client.post(f"/api/v1/db-connections/{conn_id}/test")
        assert r.status_code == 200
        data = r.json()
        # Returns 200 but success=False with an error message, not 500
        assert "success" in data

    async def test_test_nonexistent_connection_returns_404(self, client):
        r = await client.post("/api/v1/db-connections/nonexistent-id/test")
        assert r.status_code == 404


class TestQueryConnection:
    async def test_query_in_memory_sqlite(self, client):
        create_r = await client.post("/api/v1/db-connections", json={
            "name": "Query Test",
            "connection_string": "sqlite:///:memory:",
            "created_by": "tester",
        })
        conn_id = create_r.json()["id"]

        r = await client.post(f"/api/v1/db-connections/{conn_id}/query", json={
            "sql": "SELECT 1 AS value",
        })
        assert r.status_code == 200
        data = r.json()
        assert "rows" in data
        assert "columns" in data

    async def test_query_nonexistent_connection_returns_404(self, client):
        r = await client.post("/api/v1/db-connections/nonexistent/query", json={"sql": "SELECT 1"})
        assert r.status_code == 404
