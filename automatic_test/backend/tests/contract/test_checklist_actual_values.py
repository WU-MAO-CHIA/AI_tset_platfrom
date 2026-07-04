"""T240 Contract tests for ChecklistItem actual_values API (Phase 25).

TDD RED: Tests should FAIL until models/API are updated.
Covers: GET /checklists/:id/cases returns test_data + actual_values;
        PATCH /checklists/:id/cases/:case_id accepts actual_values
"""
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _admin_token(client) -> str:
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert r.status_code == 200, "需要 admin seed 帳號（admin/admin）"
    return r.json()["access_token"]


@pytest.fixture
async def auth_headers(client):
    token = await _admin_token(client)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def case_with_test_data(client, auth_headers):
    """建立含 test_data（4 欄）的測試案例，回傳 case_id。"""
    prefix = uuid.uuid4().hex[:6].upper()
    r = await client.post(
        "/api/v1/cases",
        json={
            "name": f"Checklist ActualValues Case {prefix}",
            "main_steps": "1. 執行步驟",
            "system_category": "auth",
            "created_by": "tester",
            "test_data": [
                {
                    "field_name": "username",
                    "rf_variable": "${username}",
                    "field_value": "default_user",
                    "description": "登入帳號",
                },
                {
                    "field_name": "password",
                    "rf_variable": "${password}",
                    "field_value": "default_pass",
                    "description": "登入密碼",
                },
            ],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.fixture
async def checklist_with_case(client, auth_headers, case_with_test_data):
    """建立含一個案例的清單，回傳 (checklist_id, case_id)。"""
    r = await client.post(
        "/api/v1/checklists",
        json={
            "name": f"ActualValues Checklist {uuid.uuid4().hex[:6].upper()}",
            "created_by": "tester",
            "case_ids": [case_with_test_data],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    return r.json()["id"], case_with_test_data


class TestGetChecklistCasesIncludesTestDataAndActualValues:
    async def test_list_cases_includes_test_data_array(
        self, client, auth_headers, checklist_with_case
    ):
        """GET /checklists/:id/cases 每個 item 應含 test_data 陣列。"""
        checklist_id, _ = checklist_with_case
        r = await client.get(f"/api/v1/checklists/{checklist_id}/cases", headers=auth_headers)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        item = items[0]
        assert "test_data" in item, "checklist case item 應包含 test_data"
        assert isinstance(item["test_data"], list)
        assert len(item["test_data"]) == 2

    async def test_list_cases_test_data_has_four_columns(
        self, client, auth_headers, checklist_with_case
    ):
        """GET /checklists/:id/cases test_data 每筆應含 field_name/rf_variable/field_value/description。"""
        checklist_id, _ = checklist_with_case
        r = await client.get(f"/api/v1/checklists/{checklist_id}/cases", headers=auth_headers)
        assert r.status_code == 200
        td = r.json()["items"][0]["test_data"][0]
        for col in ("field_name", "rf_variable", "field_value", "description"):
            assert col in td, f"test_data 項目缺少 {col!r}"

    async def test_list_cases_includes_actual_values_dict(
        self, client, auth_headers, checklist_with_case
    ):
        """GET /checklists/:id/cases 每個 item 應含 actual_values dict（初始為空 dict）。"""
        checklist_id, _ = checklist_with_case
        r = await client.get(f"/api/v1/checklists/{checklist_id}/cases", headers=auth_headers)
        assert r.status_code == 200
        item = r.json()["items"][0]
        assert "actual_values" in item, "checklist case item 應包含 actual_values"
        assert isinstance(item["actual_values"], dict)


class TestPatchChecklistCaseActualValues:
    async def test_patch_actual_values_persists(
        self, client, auth_headers, checklist_with_case
    ):
        """PATCH /checklists/:id/cases/:case_id 傳入 actual_values 應回 200 並持久化。"""
        checklist_id, case_id = checklist_with_case
        actual_values = {"${username}": "real_user_001", "${password}": "RealPass@123"}

        r = await client.patch(
            f"/api/v1/checklists/{checklist_id}/cases/{case_id}",
            json={"actual_values": actual_values},
            headers=auth_headers,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

        # 再次 GET 應取回持久化的值
        get_r = await client.get(f"/api/v1/checklists/{checklist_id}/cases", headers=auth_headers)
        assert get_r.status_code == 200
        item = get_r.json()["items"][0]
        assert item["actual_values"] == actual_values

    async def test_patch_actual_values_returns_updated_actual_values(
        self, client, auth_headers, checklist_with_case
    ):
        """PATCH 回應本體應包含更新後的 actual_values。"""
        checklist_id, case_id = checklist_with_case
        actual_values = {"${username}": "updated_user"}

        r = await client.patch(
            f"/api/v1/checklists/{checklist_id}/cases/{case_id}",
            json={"actual_values": actual_values},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "actual_values" in data
        assert data["actual_values"]["${username}"] == "updated_user"

    async def test_patch_null_actual_values_clears(
        self, client, auth_headers, checklist_with_case
    ):
        """PATCH 送入 actual_values: null 應清除已有值。"""
        checklist_id, case_id = checklist_with_case

        # 先設值
        await client.patch(
            f"/api/v1/checklists/{checklist_id}/cases/{case_id}",
            json={"actual_values": {"${username}": "some_user"}},
            headers=auth_headers,
        )

        # 清除
        r = await client.patch(
            f"/api/v1/checklists/{checklist_id}/cases/{case_id}",
            json={"actual_values": None},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["actual_values"] in (None, {})

    async def test_patch_invalid_case_id_returns_404(
        self, client, auth_headers, checklist_with_case
    ):
        """PATCH 使用不存在的 case_id 應回 404。"""
        checklist_id, _ = checklist_with_case
        r = await client.patch(
            f"/api/v1/checklists/{checklist_id}/cases/nonexistent-case-id",
            json={"actual_values": {"${x}": "y"}},
            headers=auth_headers,
        )
        assert r.status_code == 404
