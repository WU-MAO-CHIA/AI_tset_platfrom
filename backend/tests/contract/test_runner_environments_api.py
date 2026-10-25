"""spec 005 第一階段：執行環境管理 API 與執行時選擇環境。"""

import importlib.util
import threading
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.core.secret_box import decrypt_secret
from src.core.security import create_access_token
from src.main import app
from src.models.execution_record import ExecutionRecord
from src.models.execution_schedule import ExecutionSchedule
from src.models.runner_environment import BUILTIN_ENVIRONMENT_ID, RunnerEnvironment
from src.models.test_case import TestCase
from src.models.user import User
from src.services.runner_environment_service import reset_health_cache

TOKEN = "t" * 40
AGENT_PATH = Path(__file__).resolve().parents[3] / "runner" / "agent.py"
UNREACHABLE = "http://127.0.0.1:1"


@pytest.fixture(autouse=True)
def _clear_health():
    reset_health_cache()
    yield
    reset_health_cache()


@pytest.fixture
async def client(admin_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=admin_headers) as c:
        yield c


async def _headers_for(isolated_app, role):
    username = f"{role}1"
    async with isolated_app() as session:
        session.add(User(username=username, hashed_password="x", role=role))
        await session.commit()
    return {"Authorization": f"Bearer {create_access_token(sub=username, role=role)}"}


@pytest.fixture
def agent_url():
    spec = importlib.util.spec_from_file_location("runner_agent_contract", AGENT_PATH)
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)
    agent.Handler.token = TOKEN
    agent.Handler.run_as = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), agent.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


async def _create_env(client, **overrides):
    body = {"name": f"env-{uuid.uuid4().hex[:6]}", "kind": "linux", "url": UNREACHABLE, "token": TOKEN, **overrides}
    r = await client.post("/api/v1/runner-environments", json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def _create_case(client, **overrides):
    r = await client.post("/api/v1/cases", json={"name": "c", "main_steps": "1. x", "created_by": "admin", **overrides})
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestManage:
    async def test_list_starts_with_builtin(self, client):
        r = await client.get("/api/v1/runner-environments")
        assert r.status_code == 200
        first = r.json()["items"][0]
        assert first["id"] == BUILTIN_ENVIRONMENT_ID and first["is_builtin"] and first["kind"] == "linux"

    async def test_create_encrypts_token_and_never_returns_it(self, client, isolated_app):
        env = await _create_env(client, kind="windows", url=UNREACHABLE + "/")
        assert "token" not in env and "token_encrypted" not in env
        assert env["url"] == UNREACHABLE and env["kind"] == "windows"
        assert env["status"] == "offline"
        async with isolated_app() as session:
            row = await session.get(RunnerEnvironment, env["id"])
        assert row.token_encrypted != TOKEN and decrypt_secret(row.token_encrypted) == TOKEN
        listed = (await client.get("/api/v1/runner-environments")).text
        assert TOKEN not in listed

    @pytest.mark.parametrize("body", [
        {"kind": "mac"},
        {"url": "ftp://runner"},
        {"url": "not a url"},
        {"name": "預設容器"},
        {"token": ""},
    ])
    async def test_create_validation(self, client, body):
        r = await client.post("/api/v1/runner-environments",
                              json={"name": "x", "kind": "linux", "url": UNREACHABLE, "token": TOKEN, **body})
        assert r.status_code == 400

    async def test_duplicate_name_rejected(self, client):
        await _create_env(client, name="dup")
        r = await client.post("/api/v1/runner-environments",
                              json={"name": "dup", "kind": "linux", "url": UNREACHABLE, "token": TOKEN})
        assert r.status_code == 400

    async def test_only_admin_can_change(self, client, isolated_app):
        env = await _create_env(client)
        for role in ("viewer", "editor"):
            headers = await _headers_for(isolated_app, role)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
                assert (await c.post("/api/v1/runner-environments",
                                     json={"name": "n", "kind": "linux", "url": UNREACHABLE, "token": TOKEN})).status_code == 403
                assert (await c.put(f"/api/v1/runner-environments/{env['id']}", json={"name": "n"})).status_code == 403
                assert (await c.delete(f"/api/v1/runner-environments/{env['id']}")).status_code == 403
                listed = (await c.get("/api/v1/runner-environments")).json()["items"]
                assert all(item["url"] is None for item in listed)

    async def test_update_keeps_token_when_blank(self, client, isolated_app):
        env = await _create_env(client)
        r = await client.put(f"/api/v1/runner-environments/{env['id']}", json={"name": "renamed", "token": ""})
        assert r.status_code == 200 and r.json()["name"] == "renamed"
        async with isolated_app() as session:
            row = await session.get(RunnerEnvironment, env["id"])
        assert decrypt_secret(row.token_encrypted) == TOKEN

    async def test_builtin_cannot_be_changed(self, client):
        assert (await client.put(f"/api/v1/runner-environments/{BUILTIN_ENVIRONMENT_ID}", json={"name": "x"})).status_code == 400
        assert (await client.delete(f"/api/v1/runner-environments/{BUILTIN_ENVIRONMENT_ID}")).status_code == 400

    async def test_delete_reassigns_cases_and_schedules(self, client, isolated_app):
        linux = await _create_env(client)
        windows = await _create_env(client, kind="windows")
        linux_case = await _create_case(client, runner_environment_id=linux["id"])
        windows_case = await _create_case(client, runner_environment_id=windows["id"])
        cl = (await client.post("/api/v1/checklists", json={"name": "CL", "created_by": "admin"})).json()["id"]
        r = await client.post(f"/api/v1/checklists/{cl}/schedules", json={
            "name": "s", "frequency": "daily", "time_of_day": "02:00", "windows_environment_id": windows["id"]})
        assert r.status_code == 201, r.text

        assert (await client.delete(f"/api/v1/runner-environments/{linux['id']}")).status_code == 200
        assert (await client.delete(f"/api/v1/runner-environments/{windows['id']}")).status_code == 200

        async with isolated_app() as session:
            assert (await session.get(TestCase, linux_case)).runner_environment_id == BUILTIN_ENVIRONMENT_ID
            assert (await session.get(TestCase, windows_case)).runner_environment_id is None
            schedule = (await session.execute(select(ExecutionSchedule))).scalar_one()
            assert schedule.windows_environment_id is None

    async def test_health_check_reports_online_and_wrong_token(self, client, agent_url):
        good = await _create_env(client, url=agent_url)
        assert good["status"] == "online"
        bad = await _create_env(client, url=agent_url, token="w" * 40)
        assert bad["status"] == "unauthorized"
        r = await client.post(f"/api/v1/runner-environments/{good['id']}/check")
        assert r.status_code == 200 and r.json()["status"] == "online"


class TestSelection:
    async def test_case_default_environment(self, client):
        env = await _create_env(client, kind="windows")
        case_id = await _create_case(client)
        assert (await client.get(f"/api/v1/cases/{case_id}")).json()["runner_environment_id"] == BUILTIN_ENVIRONMENT_ID
        r = await client.put(f"/api/v1/cases/{case_id}", json={"created_by": "admin", "runner_environment_id": env["id"]})
        assert r.status_code == 200 and r.json()["runner_environment_id"] == env["id"]
        listed = (await client.get("/api/v1/cases")).json()["items"]
        assert listed[0]["runner_environment_id"] == env["id"]

    async def test_case_rejects_missing_or_disabled_environment(self, client):
        env = await _create_env(client, enabled=False)
        assert (await client.post("/api/v1/cases", json={
            "name": "c", "main_steps": "x", "created_by": "admin", "runner_environment_id": "nope"})).status_code == 400
        assert (await client.post("/api/v1/cases", json={
            "name": "c", "main_steps": "x", "created_by": "admin", "runner_environment_id": env["id"]})).status_code == 400

    async def test_trial_run_override_must_match_kind(self, client, isolated_app):
        linux = await _create_env(client)
        windows = await _create_env(client, kind="windows")
        case_id = await _create_case(client)
        code = "*** Test Cases ***\nT\n    Log    x\n"

        r = await client.post(f"/api/v1/cases/{case_id}/trial-run", json={"rf_code": code, "environment_id": windows["id"]})
        assert r.status_code == 400
        r = await client.post(f"/api/v1/cases/{case_id}/trial-run", json={"rf_code": code, "environment_id": linux["id"]})
        assert r.status_code == 202
        async with isolated_app() as session:
            record = await session.get(ExecutionRecord, r.json()["execution_id"])
        assert record.params["environment_id"] == linux["id"]

    async def test_trial_run_requires_environment_after_deletion(self, client):
        windows = await _create_env(client, kind="windows")
        other = await _create_env(client, kind="windows")
        case_id = await _create_case(client, runner_environment_id=windows["id"])
        await client.delete(f"/api/v1/runner-environments/{windows['id']}")
        code = "*** Test Cases ***\nT\n    Log    x\n"

        r = await client.post(f"/api/v1/cases/{case_id}/trial-run", json={"rf_code": code})
        assert r.status_code == 422 and r.json()["detail"]["error"] == "no_environment"
        r = await client.post(f"/api/v1/cases/{case_id}/trial-run", json={"rf_code": code, "environment_id": other["id"]})
        assert r.status_code == 202

    async def test_checklist_execute_overrides(self, client, isolated_app):
        linux = await _create_env(client)
        windows = await _create_env(client, kind="windows")
        case_id = await _create_case(client)
        cl = (await client.post("/api/v1/checklists", json={"name": "CL", "created_by": "admin"})).json()["id"]
        await client.post(f"/api/v1/checklists/{cl}/cases", json={"case_id": case_id})

        r = await client.post(f"/api/v1/checklists/{cl}/execute", json={"linux_environment_id": windows["id"]})
        assert r.status_code == 400
        r = await client.post(f"/api/v1/checklists/{cl}/execute", json={
            "linux_environment_id": linux["id"], "windows_environment_id": windows["id"]})
        assert r.status_code == 202
        async with isolated_app() as session:
            record = await session.get(ExecutionRecord, r.json()["execution_id"])
        assert record.params["environment_overrides"] == {"linux": linux["id"], "windows": windows["id"]}

    async def test_schedule_environment_must_match_kind(self, client):
        linux = await _create_env(client)
        cl = (await client.post("/api/v1/checklists", json={"name": "CL", "created_by": "admin"})).json()["id"]
        base = {"name": "s", "frequency": "daily", "time_of_day": "02:00"}
        r = await client.post(f"/api/v1/checklists/{cl}/schedules", json={**base, "windows_environment_id": linux["id"]})
        assert r.status_code in (400, 422)
        r = await client.post(f"/api/v1/checklists/{cl}/schedules", json={**base, "linux_environment_id": linux["id"]})
        assert r.status_code == 201 and r.json()["linux_environment_id"] == linux["id"]
        r = await client.put(f"/api/v1/schedules/{r.json()['id']}", json={"linux_environment_id": None})
        assert r.status_code == 200 and r.json()["linux_environment_id"] is None
