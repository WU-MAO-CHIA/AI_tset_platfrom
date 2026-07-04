"""Contract tests for GET /cases (list + filter) and GET /cases/{id}/execution-history.
RED: Tests should fail until the endpoints are implemented.
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def seeded_cases(client):
    prefix = uuid.uuid4().hex[:6].upper()
    cases = [
        {"case_number": f"TC-L{prefix}-1", "name": f"Auth Login {prefix}", "main_steps": "steps", "system_category": "auth", "created_by": "t"},
        {"case_number": f"TC-L{prefix}-2", "name": f"Auth Logout {prefix}", "main_steps": "steps", "system_category": "auth", "created_by": "t"},
        {"case_number": f"TC-L{prefix}-3", "name": f"Order Create {prefix}", "main_steps": "steps", "system_category": "order", "created_by": "t"},
    ]
    ids = []
    for c in cases:
        r = await client.post("/api/v1/cases", json=c)
        assert r.status_code == 201, f"Seed failed: {r.text}"
        ids.append(r.json()["id"])
    return ids


class TestCaseListFilters:
    async def test_list_all_cases(self, client, seeded_cases):
        response = await client.get("/api/v1/cases")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 3

    async def test_filter_by_system_category(self, client, seeded_cases):
        response = await client.get("/api/v1/cases", params={"system_category": "auth"})
        assert response.status_code == 200
        items = response.json()["items"]
        assert all(item["system_category"] == "auth" for item in items)
        assert len(items) >= 2

    async def test_filter_by_keyword(self, client, seeded_cases):
        response = await client.get("/api/v1/cases", params={"keyword": "Auth"})
        assert response.status_code == 200
        items = response.json()["items"]
        assert all("auth" in item["name"].lower() for item in items)

    async def test_pagination(self, client, seeded_cases):
        response = await client.get("/api/v1/cases", params={"page": 1, "page_size": 2})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_empty_result_with_no_match(self, client, seeded_cases):
        response = await client.get("/api/v1/cases", params={"keyword": "XXXXXXXX_nonexistent"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestCaseExecutionHistory:
    async def test_execution_history_returns_structure(self, client, seeded_cases):
        case_id = seeded_cases[0]
        response = await client.get(f"/api/v1/cases/{case_id}/execution-history")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 0  # No executions yet

    async def test_execution_history_404_for_missing_case(self, client):
        response = await client.get("/api/v1/cases/nonexistent/execution-history")
        assert response.status_code == 404
