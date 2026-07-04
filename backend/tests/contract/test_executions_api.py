"""Contract tests for execution endpoints.
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
async def created_checklist(client):
    prefix = uuid.uuid4().hex[:6].upper()
    case_r = await client.post("/api/v1/cases", json={
        "case_number": f"EX-CASE-{prefix}",
        "name": "Execution Test Case",
        "main_steps": "1. Open browser\n2. Navigate to URL",
        "created_by": "tester",
    })
    assert case_r.status_code == 201

    cl_r = await client.post("/api/v1/checklists", json={
        "name": f"Exec Checklist {prefix}",
        "created_by": "tester",
        "case_ids": [case_r.json()["id"]],
    })
    assert cl_r.status_code == 201
    return cl_r.json()["id"]


class TestExecuteChecklist:
    async def test_execute_returns_202(self, client, created_checklist):
        r = await client.post(f"/api/v1/checklists/{created_checklist}/execute", json={
            "parallel_mode": False,
            "max_workers": 1,
        })
        assert r.status_code == 202
        data = r.json()
        assert "execution_id" in data
        assert "stream_url" in data

    async def test_execute_nonexistent_checklist_returns_404(self, client):
        r = await client.post("/api/v1/checklists/nonexistent/execute", json={
            "parallel_mode": False,
            "max_workers": 1,
        })
        assert r.status_code == 404


class TestGetExecution:
    async def test_get_execution_returns_record(self, client, created_checklist):
        exec_r = await client.post(f"/api/v1/checklists/{created_checklist}/execute", json={
            "parallel_mode": False,
            "max_workers": 1,
        })
        execution_id = exec_r.json()["execution_id"]

        r = await client.get(f"/api/v1/executions/{execution_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == execution_id
        assert "status" in data
        assert "checklist_id" in data

    async def test_get_nonexistent_execution_returns_404(self, client):
        r = await client.get("/api/v1/executions/nonexistent")
        assert r.status_code == 404


class TestGetExecutionResults:
    async def test_get_results_returns_list(self, client, created_checklist):
        exec_r = await client.post(f"/api/v1/checklists/{created_checklist}/execute", json={
            "parallel_mode": False,
            "max_workers": 1,
        })
        execution_id = exec_r.json()["execution_id"]

        r = await client.get(f"/api/v1/executions/{execution_id}/results")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data


class TestExportReport:
    async def test_export_returns_html(self, client, created_checklist):
        exec_r = await client.post(f"/api/v1/checklists/{created_checklist}/execute", json={
            "parallel_mode": False,
            "max_workers": 1,
        })
        execution_id = exec_r.json()["execution_id"]

        r = await client.get(f"/api/v1/executions/{execution_id}/export")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert "content-disposition" in r.headers
