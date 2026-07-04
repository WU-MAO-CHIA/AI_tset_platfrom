"""T239 Contract tests for TestData 4-column API (Phase 25).

TDD RED: Tests should FAIL until models/API are updated.
Covers: rf_variable, description fields on TestData
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
def case_with_test_data():
    prefix = uuid.uuid4().hex[:6].upper()
    return {
        "name": f"TestData 4-column case {prefix}",
        "main_steps": "1. 開啟頁面\n2. 填入資料\n3. 送出",
        "system_category": "auth",
        "created_by": "tester_phase25",
        "test_data": [
            {
                "field_name": "username",
                "rf_variable": "${username}",
                "field_value": "testuser@example.com",
                "description": "登入帳號",
            },
            {
                "field_name": "password",
                "rf_variable": "${password}",
                "field_value": "P@ssw0rd",
                "description": "登入密碼",
            },
        ],
    }


class TestCreateCaseWithTestDataFourColumns:
    async def test_create_case_with_rf_variable_and_description(
        self, client, auth_headers, case_with_test_data
    ):
        """POST /cases 應接受含 rf_variable 與 description 的 test_data 欄位。"""
        r = await client.post("/api/v1/cases", json=case_with_test_data, headers=auth_headers)
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"

    async def test_create_case_test_data_without_rf_variable(
        self, client, auth_headers
    ):
        """rf_variable 為 null 時應仍可建立（nullable）。"""
        prefix = uuid.uuid4().hex[:6].upper()
        payload = {
            "name": f"NoRfVar case {prefix}",
            "main_steps": "step",
            "system_category": "auth",
            "created_by": "tester",
            "test_data": [
                {
                    "field_name": "env",
                    "field_value": "production",
                    "rf_variable": None,
                    "description": None,
                }
            ],
        }
        r = await client.post("/api/v1/cases", json=payload, headers=auth_headers)
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"


class TestGetCaseReturnsFourColumnTestData:
    async def test_get_case_test_data_includes_rf_variable(
        self, client, auth_headers, case_with_test_data
    ):
        """GET /cases/:id 回傳的 test_data 陣列中每筆應包含 rf_variable 欄位。"""
        create_r = await client.post("/api/v1/cases", json=case_with_test_data, headers=auth_headers)
        assert create_r.status_code == 201
        case_id = create_r.json()["id"]

        r = await client.get(f"/api/v1/cases/{case_id}", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "test_data" in data, "回應應包含 test_data 欄位"
        assert len(data["test_data"]) == 2
        first = data["test_data"][0]
        assert "rf_variable" in first, "test_data 項目應包含 rf_variable"
        assert first["rf_variable"] == "${username}"

    async def test_get_case_test_data_includes_description(
        self, client, auth_headers, case_with_test_data
    ):
        """GET /cases/:id 回傳的 test_data 陣列中每筆應包含 description 欄位。"""
        create_r = await client.post("/api/v1/cases", json=case_with_test_data, headers=auth_headers)
        assert create_r.status_code == 201
        case_id = create_r.json()["id"]

        r = await client.get(f"/api/v1/cases/{case_id}", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        first = data["test_data"][0]
        assert "description" in first, "test_data 項目應包含 description"
        assert first["description"] == "登入帳號"

    async def test_get_case_test_data_has_all_four_columns(
        self, client, auth_headers, case_with_test_data
    ):
        """GET /cases/:id test_data 每筆應同時包含 field_name/rf_variable/field_value/description 四欄。"""
        create_r = await client.post("/api/v1/cases", json=case_with_test_data, headers=auth_headers)
        assert create_r.status_code == 201
        case_id = create_r.json()["id"]

        r = await client.get(f"/api/v1/cases/{case_id}", headers=auth_headers)
        assert r.status_code == 200
        for item in r.json()["test_data"]:
            for col in ("field_name", "rf_variable", "field_value", "description"):
                assert col in item, f"test_data 項目缺少欄位 {col!r}"
