"""Contract tests for /api/v1/checklists endpoints.
RED: Tests should fail until the API is implemented.
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
async def created_case(client):
    prefix = uuid.uuid4().hex[:6].upper()
    r = await client.post("/api/v1/cases", json={
        "case_number": f"CL-CASE-{prefix}",
        "name": f"Case for Checklist {prefix}",
        "main_steps": "steps",
        "created_by": "tester",
    })
    assert r.status_code == 201
    return r.json()["id"]


class TestCreateChecklist:
    async def test_create_checklist_returns_201(self, client, created_case):
        r = await client.post("/api/v1/checklists", json={
            "name": "Sprint 1 Tests",
            "created_by": "tester",
            "case_ids": [created_case],
        })
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Sprint 1 Tests"
        assert "id" in data

    async def test_create_checklist_missing_name_returns_422(self, client):
        r = await client.post("/api/v1/checklists", json={"created_by": "t", "case_ids": []})
        assert r.status_code == 422


class TestGetChecklist:
    async def test_get_checklist_includes_items(self, client, created_case):
        create_r = await client.post("/api/v1/checklists", json={
            "name": "My Checklist",
            "created_by": "tester",
            "case_ids": [created_case],
        })
        cl_id = create_r.json()["id"]

        r = await client.get(f"/api/v1/checklists/{cl_id}")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert len(data["items"]) == 1

    async def test_get_nonexistent_checklist_returns_404(self, client):
        r = await client.get("/api/v1/checklists/nonexistent-id")
        assert r.status_code == 404


class TestUpdateChecklistItems:
    async def test_update_items_replaces_case_list(self, client, created_case):
        create_r = await client.post("/api/v1/checklists", json={
            "name": "Update Test",
            "created_by": "tester",
            "case_ids": [created_case],
        })
        cl_id = create_r.json()["id"]

        # Remove the case
        r = await client.put(f"/api/v1/checklists/{cl_id}/items", json={"case_ids": []})
        assert r.status_code == 200

        detail_r = await client.get(f"/api/v1/checklists/{cl_id}")
        assert len(detail_r.json()["items"]) == 0
