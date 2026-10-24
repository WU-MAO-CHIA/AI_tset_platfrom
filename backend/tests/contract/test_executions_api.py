"""Contract tests for execution endpoints.
RED: Tests should fail until the API is implemented.
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client(admin_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=admin_headers) as c:
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


class TestCancelExecution:
    async def _execute(self, client, checklist_id) -> str:
        r = await client.post(f"/api/v1/checklists/{checklist_id}/execute", json={
            "parallel_mode": False,
            "max_workers": 1,
        })
        assert r.status_code == 202
        return r.json()["execution_id"]

    async def test_cancel_pending_execution(self, client, created_checklist, isolated_app):
        from sqlalchemy import select
        from src.models.execution_event import ExecutionEvent

        execution_id = await self._execute(client, created_checklist)

        r = await client.post(f"/api/v1/executions/{execution_id}/cancel")
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

        async with isolated_app() as session:
            events = (await session.execute(
                select(ExecutionEvent)
                .where(ExecutionEvent.execution_id == execution_id)
                .order_by(ExecutionEvent.id)
            )).scalars().all()
        assert events[-1].event == "execution_cancelled"
        assert events[-1].payload["__done__"] is True

    async def test_cancel_updates_queue_positions(self, client, created_checklist, isolated_app):
        from sqlalchemy import select
        from src.models.execution_event import ExecutionEvent

        first = await self._execute(client, created_checklist)
        second = await self._execute(client, created_checklist)

        r = await client.post(f"/api/v1/executions/{first}/cancel")
        assert r.status_code == 200

        async with isolated_app() as session:
            last = (await session.execute(
                select(ExecutionEvent)
                .where(ExecutionEvent.execution_id == second, ExecutionEvent.event == "execution_queued")
                .order_by(ExecutionEvent.id.desc())
            )).scalars().first()
        assert last.payload["ahead"] == 0

    async def test_cancel_twice_returns_409(self, client, created_checklist):
        execution_id = await self._execute(client, created_checklist)
        assert (await client.post(f"/api/v1/executions/{execution_id}/cancel")).status_code == 200

        r = await client.post(f"/api/v1/executions/{execution_id}/cancel")
        assert r.status_code == 409

    async def test_cancel_running_returns_409(self, client, created_checklist, isolated_app):
        from sqlalchemy import update
        from src.models.execution_record import ExecutionRecord

        execution_id = await self._execute(client, created_checklist)
        async with isolated_app() as session:
            await session.execute(
                update(ExecutionRecord).where(ExecutionRecord.id == execution_id).values(status="running")
            )
            await session.commit()

        r = await client.post(f"/api/v1/executions/{execution_id}/cancel")
        assert r.status_code == 409
        assert r.json()["detail"]["status"] == "running"

    async def test_cancel_nonexistent_returns_404(self, client):
        r = await client.post("/api/v1/executions/nonexistent/cancel")
        assert r.status_code == 404

    async def test_viewer_cannot_cancel(self, client, created_checklist, isolated_app):
        from src.core.security import create_access_token, hash_password
        from src.models.user import User

        execution_id = await self._execute(client, created_checklist)
        async with isolated_app() as session:
            session.add(User(username="cancel_viewer", hashed_password=hash_password("x"), role="viewer"))
            await session.commit()
        token = create_access_token(sub="cancel_viewer", role="viewer")

        r = await client.post(
            f"/api/v1/executions/{execution_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403
