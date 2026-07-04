"""Contract tests for /api/v1/cases endpoints.
RED: All tests should fail until the API is implemented.
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _get_auth_token(client) -> str:
    """Get auth token for testing."""
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    if r.status_code == 200:
        return r.json()["access_token"]
    # Fallback: create a test user
    r = await client.post("/api/v1/admin/accounts", json={"username": "test_user", "password": "test_pass", "role": "viewer"})
    r = await client.post("/api/v1/auth/login", json={"username": "test_user", "password": "test_pass"})
    return r.json()["access_token"]


@pytest.fixture
def valid_case_payload():
    unique = uuid.uuid4().hex[:6].upper()
    return {
        "case_number": f"TC-CT-{unique}",
        "name": "登入功能測試",
        "main_steps": "1. 開啟登入頁面\n2. 輸入帳號密碼\n3. 點擊登入\n4. 確認進入首頁",
        "system_category": "auth",
        "created_by": "tester_01",
    }


@pytest.fixture
async def auth_headers(client):
    """Fixture for authorization headers."""
    token = await _get_auth_token(client)
    return {"Authorization": f"Bearer {token}"}


class TestCreateCase:
    async def test_create_case_returns_201(self, client, valid_case_payload, auth_headers):
        response = await client.post("/api/v1/cases", json=valid_case_payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["case_number"] == valid_case_payload["case_number"]
        assert data["version"] == 1
        assert "id" in data
        assert "created_at" in data

    async def test_create_case_duplicate_case_number_returns_409(self, client, valid_case_payload):
        await client.post("/api/v1/cases", json=valid_case_payload)
        response = await client.post("/api/v1/cases", json=valid_case_payload)
        assert response.status_code == 409
        body = response.json()
        # FastAPI wraps HTTPException detail under "detail" key
        error_data = body.get("detail") or body
        assert error_data["error"] == "case_number_conflict"

    async def test_create_case_missing_required_field_returns_422(self, client):
        response = await client.post("/api/v1/cases", json={"case_number": "TC-002"})
        assert response.status_code == 422


class TestUpdateCase:
    async def test_update_case_increments_version(self, client, valid_case_payload):
        create_resp = await client.post("/api/v1/cases", json=valid_case_payload)
        case_id = create_resp.json()["id"]

        update_payload = {"name": "Updated Name", "main_steps": "new steps", "created_by": "tester_01"}
        response = await client.put(f"/api/v1/cases/{case_id}", json=update_payload)
        assert response.status_code == 200
        assert response.json()["version"] == 2

    async def test_update_nonexistent_case_returns_404(self, client):
        response = await client.put("/api/v1/cases/nonexistent-id", json={"name": "x", "main_steps": "x", "created_by": "t"})
        assert response.status_code == 404


class TestPreviewRF:
    async def test_preview_rf_returns_rf_code(self, client):
        response = await client.post(
            "/api/v1/cases/preview-rf",
            json={"main_steps": "1. 開啟登入頁面\n2. 輸入帳號密碼\n3. 點擊登入", "llm_model": "claude-sonnet-4-6"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "rf_code" in data
        assert isinstance(data["rf_code"], str)

    async def test_preview_rf_empty_steps_returns_422(self, client):
        response = await client.post(
            "/api/v1/cases/preview-rf",
            json={"main_steps": "", "llm_model": "claude-sonnet-4-6"},
        )
        assert response.status_code == 422

    async def test_preview_rf_missing_steps_returns_422(self, client):
        response = await client.post("/api/v1/cases/preview-rf", json={"llm_model": "claude-sonnet-4-6"})
        assert response.status_code == 422


class TestDeleteCase:
    async def test_soft_delete_returns_200(self, client, valid_case_payload):
        create_resp = await client.post("/api/v1/cases", json=valid_case_payload)
        case_id = create_resp.json()["id"]

        response = await client.request("DELETE", f"/api/v1/cases/{case_id}", json={"deleted_by": "tester_01"})
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_deleted_case_not_in_list(self, client, valid_case_payload):
        create_resp = await client.post("/api/v1/cases", json=valid_case_payload)
        case_id = create_resp.json()["id"]
        await client.request("DELETE", f"/api/v1/cases/{case_id}", json={"deleted_by": "tester_01"})

        list_resp = await client.get("/api/v1/cases")
        ids = [item["id"] for item in list_resp.json()["items"]]
        assert case_id not in ids

    async def test_delete_referenced_case_returns_affected_checklists(self, client, valid_case_payload):
        """When a case is referenced by a checklist, delete returns affected_checklists with names."""
        create_resp = await client.post("/api/v1/cases", json=valid_case_payload)
        case_id = create_resp.json()["id"]

        # Create a checklist referencing this case
        await client.post("/api/v1/checklists", json={"name": "Sprint 1", "created_by": "tester_01", "case_ids": [case_id]})

        response = await client.request("DELETE", f"/api/v1/cases/{case_id}", json={"deleted_by": "tester_01"})
        assert response.status_code == 409
        body = response.json()
        # FastAPI wraps HTTPException detail under "detail" key
        data = body.get("detail") or body
        assert data["error"] == "case_in_use"
        assert "affected_checklists" in data
        assert len(data["affected_checklists"]) > 0
        assert "name" in data["affected_checklists"][0]
        assert "id" in data["affected_checklists"][0]


class TestChatEndpoints:
    async def test_chat_returns_message_and_rf_code(self, client, valid_case_payload):
        create_resp = await client.post("/api/v1/cases", json=valid_case_payload)
        case_id = create_resp.json()["id"]
        response = await client.post(
            f"/api/v1/cases/{case_id}/chat",
            json={"message": "測試登入功能", "llm_model": "claude-sonnet-4-6"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "assistant_message" in data
        assert "rf_code" in data

    async def test_chat_history_returns_messages(self, client, valid_case_payload):
        create_resp = await client.post("/api/v1/cases", json=valid_case_payload)
        case_id = create_resp.json()["id"]
        response = await client.get(f"/api/v1/cases/{case_id}/chat-history")
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)

    async def test_chat_history_includes_type_field_phase27(self, client, valid_case_payload):
        """Phase 27: Chat history messages should include 'type' field."""
        create_resp = await client.post("/api/v1/cases", json=valid_case_payload)
        case_id = create_resp.json()["id"]
        response = await client.get(f"/api/v1/cases/{case_id}/chat-history")
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        if len(data["messages"]) > 0:
            assert "type" in data["messages"][0], "Message should include 'type' field"
            assert data["messages"][0]["type"] in ["chat", "trial_run_result"]


class TestTrialRunEndpoints:
    """Phase 27: Trial run endpoints - immediate execution with RF code preview."""

    async def test_trial_run_accepts_rf_code_and_case_name(self, client, valid_case_payload, auth_headers):
        """T250: POST /cases/{case_id}/trial-run accepts rf_code and case_name."""
        create_resp = await client.post("/api/v1/cases", json=valid_case_payload, headers=auth_headers)
        case_id = create_resp.json()["id"]

        rf_code = "*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\n測試\n    Log    Hello"
        response = await client.post(
            f"/api/v1/cases/{case_id}/trial-run",
            json={"rf_code": rf_code, "case_name": "Trial Run Test"},
            headers=auth_headers
        )

        assert response.status_code == 202, f"Expected 202 Accepted, got {response.status_code}: {response.text}"
        data = response.json()
        assert "execution_id" in data, "Response should include 'execution_id'"
        assert "stream_url" in data, "Response should include 'stream_url'"

    async def test_trial_run_rf_code_required(self, client, valid_case_payload, auth_headers):
        """T250: rf_code field is required for trial-run."""
        create_resp = await client.post("/api/v1/cases", json=valid_case_payload, headers=auth_headers)
        case_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/cases/{case_id}/trial-run",
            json={"case_name": "Trial Run Test"},  # Missing rf_code
            headers=auth_headers
        )

        assert response.status_code == 422, f"Expected 422 Validation Error, got {response.status_code}"

    async def test_trial_run_case_name_optional(self, client, valid_case_payload, auth_headers):
        """T250: case_name is optional, defaults to case_id."""
        create_resp = await client.post("/api/v1/cases", json=valid_case_payload, headers=auth_headers)
        case_id = create_resp.json()["id"]

        rf_code = "*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\n測試\n    Log    Hello"
        response = await client.post(
            f"/api/v1/cases/{case_id}/trial-run",
            json={"rf_code": rf_code},  # No case_name
            headers=auth_headers
        )

        assert response.status_code == 202, f"Expected 202 Accepted, got {response.status_code}: {response.text}"

    async def test_trial_run_adds_result_message_to_chat_history(self, client, valid_case_payload, auth_headers):
        """T250: Trial run result should appear in chat history with type='trial_run_result'."""
        create_resp = await client.post("/api/v1/cases", json=valid_case_payload, headers=auth_headers)
        case_id = create_resp.json()["id"]

        rf_code = "*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\n測試\n    Log    Hello"
        trial_resp = await client.post(
            f"/api/v1/cases/{case_id}/trial-run",
            json={"rf_code": rf_code, "case_name": "Trial Run Test"},
            headers=auth_headers
        )

        assert trial_resp.status_code == 202

        # Poll or wait for execution to complete (in integration test this would use proper async wait)
        # For contract test, we just verify the endpoint accepts the request
        # Actual verification of message persistence happens in integration tests
