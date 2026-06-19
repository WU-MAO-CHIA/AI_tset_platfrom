"""Contract tests for FR-023 checklist CRUD + case management endpoints.
TDD RED: Tests should pass once the API endpoints are implemented.
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
        "name": f"CRUD Test Case {prefix}",
        "main_steps": "1. Open browser\n2. Navigate to page",
        "system_category": "crud",
        "created_by": "tester",
    })
    assert r.status_code == 201
    return r.json()["id"]


@pytest.fixture
async def created_case2(client):
    prefix = uuid.uuid4().hex[:6].upper()
    r = await client.post("/api/v1/cases", json={
        "name": f"CRUD Test Case B {prefix}",
        "main_steps": "1. Step one",
        "system_category": "crud",
        "created_by": "tester",
    })
    assert r.status_code == 201
    return r.json()["id"]


@pytest.fixture
async def created_checklist(client, created_case):
    r = await client.post("/api/v1/checklists", json={
        "name": "CRUD Test Checklist",
        "created_by": "tester",
        "case_ids": [created_case],
    })
    assert r.status_code == 201
    return r.json()["id"]


class TestUpdateChecklist:
    async def test_put_checklist_updates_name(self, client, created_checklist):
        r = await client.put(f"/api/v1/checklists/{created_checklist}", json={
            "name": "Updated Checklist Name",
            "created_by": "tester",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Updated Checklist Name"

    async def test_put_checklist_updates_created_by(self, client, created_checklist):
        r = await client.put(f"/api/v1/checklists/{created_checklist}", json={
            "name": "CRUD Test Checklist",
            "created_by": "new_tester",
        })
        assert r.status_code == 200
        assert r.json()["created_by"] == "new_tester"

    async def test_put_nonexistent_checklist_returns_404(self, client):
        r = await client.put("/api/v1/checklists/nonexistent", json={
            "name": "X",
            "created_by": "t",
        })
        assert r.status_code == 404


class TestDeleteChecklist:
    async def test_delete_checklist_returns_200(self, client, created_checklist):
        r = await client.delete(f"/api/v1/checklists/{created_checklist}")
        assert r.status_code == 200
        assert r.json()["success"] is True

    async def test_delete_checklist_makes_it_not_found(self, client, created_checklist):
        await client.delete(f"/api/v1/checklists/{created_checklist}")
        r = await client.get(f"/api/v1/checklists/{created_checklist}")
        assert r.status_code == 404

    async def test_delete_nonexistent_checklist_returns_404(self, client):
        r = await client.delete("/api/v1/checklists/nonexistent")
        assert r.status_code == 404


class TestGetChecklistCases:
    async def test_get_cases_returns_items_with_notes(self, client, created_checklist):
        r = await client.get(f"/api/v1/checklists/{created_checklist}/cases")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert "item_id" in item
        assert "test_case_id" in item
        assert "position" in item
        assert "notes" in item

    async def test_get_cases_nonexistent_checklist_returns_404(self, client):
        r = await client.get("/api/v1/checklists/nonexistent/cases")
        assert r.status_code == 404


class TestAddCaseToChecklist:
    async def test_post_case_adds_to_checklist(self, client, created_checklist, created_case2):
        r = await client.post(f"/api/v1/checklists/{created_checklist}/cases", json={
            "case_id": created_case2,
            "position": None,
        })
        assert r.status_code == 201
        data = r.json()
        assert "item_id" in data
        assert "position" in data

    async def test_post_duplicate_case_returns_409(self, client, created_checklist, created_case):
        r = await client.post(f"/api/v1/checklists/{created_checklist}/cases", json={
            "case_id": created_case,
        })
        assert r.status_code == 409

    async def test_post_nonexistent_case_returns_404(self, client, created_checklist):
        r = await client.post(f"/api/v1/checklists/{created_checklist}/cases", json={
            "case_id": "nonexistent-case",
        })
        assert r.status_code == 404


class TestRemoveCaseFromChecklist:
    async def test_delete_case_removes_from_checklist(self, client, created_checklist, created_case):
        r = await client.delete(f"/api/v1/checklists/{created_checklist}/cases/{created_case}")
        assert r.status_code == 200
        assert r.json()["success"] is True

        cases_r = await client.get(f"/api/v1/checklists/{created_checklist}/cases")
        assert cases_r.json()["total"] == 0

    async def test_delete_nonexistent_case_returns_404(self, client, created_checklist):
        r = await client.delete(f"/api/v1/checklists/{created_checklist}/cases/nonexistent")
        assert r.status_code == 404


class TestPatchChecklistCaseItem:
    async def test_patch_notes_updates_item(self, client, created_checklist, created_case):
        cases_r = await client.get(f"/api/v1/checklists/{created_checklist}/cases")
        item_id = cases_r.json()["items"][0]["item_id"]

        r = await client.patch(
            f"/api/v1/checklists/{created_checklist}/cases/{created_case}",
            json={"notes": "此清單專用備註"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["notes"] == "此清單專用備註"

    async def test_patch_position_updates_order(self, client, created_checklist, created_case, created_case2):
        await client.post(f"/api/v1/checklists/{created_checklist}/cases", json={"case_id": created_case2})
        r = await client.patch(
            f"/api/v1/checklists/{created_checklist}/cases/{created_case}",
            json={"position": 2},
        )
        assert r.status_code == 200
        assert r.json()["position"] == 2


class TestReorderChecklistCases:
    async def test_reorder_cases_returns_200(self, client, created_checklist, created_case, created_case2):
        await client.post(f"/api/v1/checklists/{created_checklist}/cases", json={"case_id": created_case2})
        r = await client.put(
            f"/api/v1/checklists/{created_checklist}/cases/reorder",
            json={"case_ids": [created_case2, created_case]},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

    async def test_reorder_reflects_new_order(self, client, created_checklist, created_case, created_case2):
        await client.post(f"/api/v1/checklists/{created_checklist}/cases", json={"case_id": created_case2})
        await client.put(
            f"/api/v1/checklists/{created_checklist}/cases/reorder",
            json={"case_ids": [created_case2, created_case]},
        )
        cases_r = await client.get(f"/api/v1/checklists/{created_checklist}/cases")
        items = sorted(cases_r.json()["items"], key=lambda x: x["position"])
        assert items[0]["test_case_id"] == created_case2
        assert items[1]["test_case_id"] == created_case
