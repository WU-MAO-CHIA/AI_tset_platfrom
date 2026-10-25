"""spec 004 第 2 階段：排程 CRUD API。"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.security import create_access_token
from src.main import app
from src.models.execution_record import ExecutionRecord
from src.models.execution_schedule import ExecutionSchedule
from src.models.user import User
from src.scheduling.timing import as_utc

DAILY = {"name": "nightly", "frequency": "daily", "time_of_day": "02:00"}


@pytest.fixture
async def client(admin_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=admin_headers) as c:
        yield c


@pytest.fixture
async def viewer_headers(isolated_app):
    async with isolated_app() as session:
        session.add(User(username="viewer1", hashed_password="x", role="viewer"))
        await session.commit()
    return {"Authorization": f"Bearer {create_access_token(sub='viewer1', role='viewer')}"}


@pytest.fixture
async def checklist_id(client):
    r = await client.post("/api/v1/checklists", json={"name": f"CL {uuid.uuid4().hex[:6]}", "created_by": "tester"})
    assert r.status_code == 201
    return r.json()["id"]


async def _create(client, checklist_id, **overrides):
    return await client.post(f"/api/v1/checklists/{checklist_id}/schedules", json={**DAILY, **overrides})


class TestCreate:
    async def test_create_daily_computes_next_run(self, client, checklist_id):
        r = await _create(client, checklist_id, parallel_mode=True, max_workers=2)

        assert r.status_code == 201
        data = r.json()
        assert data["checklist_id"] == checklist_id
        assert data["checklist_name"].startswith("CL ")
        assert data["enabled"] is True
        assert data["created_by"] == "admin"
        assert data["timezone"] == "Asia/Taipei"
        assert data["parallel_mode"] is True and data["max_workers"] == 2
        next_run = datetime.fromisoformat(data["next_run_at"])
        now = datetime.now(timezone.utc)
        assert now < next_run <= now + timedelta(days=1)
        # 台北 02:00 = UTC 18:00
        assert (next_run.hour, next_run.minute) == (18, 0)

    async def test_create_weekly_normalizes_weekdays(self, client, checklist_id):
        r = await _create(client, checklist_id, frequency="weekly", weekdays=[4, 0, 4], interval_minutes=30)
        assert r.status_code == 201
        assert r.json()["weekdays"] == [0, 4]
        assert r.json()["interval_minutes"] is None

    async def test_create_interval_drops_time_of_day(self, client, checklist_id):
        r = await _create(client, checklist_id, frequency="interval", interval_minutes=60)
        assert r.status_code == 201
        assert r.json()["time_of_day"] is None
        assert r.json()["interval_minutes"] == 60

    async def test_create_disabled_has_no_next_run(self, client, checklist_id):
        r = await _create(client, checklist_id, enabled=False)
        assert r.status_code == 201
        assert r.json()["next_run_at"] is None

    @pytest.mark.parametrize("overrides", [
        {"frequency": "hourly"},
        {"time_of_day": "25:00"},
        {"frequency": "weekly", "weekdays": []},
        {"frequency": "interval", "interval_minutes": 5},
        {"name": "   "},
        {"max_workers": 0},
        {"max_workers": 99},
    ])
    async def test_invalid_returns_400(self, client, checklist_id, overrides):
        r = await _create(client, checklist_id, **overrides)
        assert r.status_code == 400
        assert r.json()["error"] == "validation_error"

    async def test_unknown_checklist_returns_404(self, client):
        assert (await _create(client, "missing")).status_code == 404


class TestList:
    async def test_list_all_and_per_checklist(self, client, checklist_id):
        other = (await client.post("/api/v1/checklists", json={"name": "other", "created_by": "t"})).json()["id"]
        await _create(client, checklist_id)
        await _create(client, other, name="other-sched")

        all_r = await client.get("/api/v1/schedules")
        assert all_r.status_code == 200
        assert all_r.json()["total"] == 2

        one = await client.get(f"/api/v1/checklists/{checklist_id}/schedules")
        assert [s["name"] for s in one.json()["items"]] == ["nightly"]

    async def test_list_unknown_checklist_returns_404(self, client):
        assert (await client.get("/api/v1/checklists/missing/schedules")).status_code == 404

    async def test_shows_last_execution_status(self, client, checklist_id, isolated_app):
        schedule_id = (await _create(client, checklist_id)).json()["id"]
        async with isolated_app() as session:
            session.add(ExecutionRecord(id="exec-1", checklist_id=checklist_id, status="completed", schedule_id=schedule_id))
            schedule = await session.get(ExecutionSchedule, schedule_id)
            schedule.last_execution_id = "exec-1"
            await session.commit()

        item = (await client.get("/api/v1/schedules")).json()["items"][0]
        assert item["last_execution_id"] == "exec-1"
        assert item["last_execution_status"] == "completed"


class TestUpdate:
    async def test_disable_clears_next_run_and_enable_recomputes(self, client, checklist_id):
        schedule_id = (await _create(client, checklist_id)).json()["id"]

        off = await client.put(f"/api/v1/schedules/{schedule_id}", json={"enabled": False})
        assert off.status_code == 200
        assert off.json()["enabled"] is False
        assert off.json()["next_run_at"] is None

        on = await client.put(f"/api/v1/schedules/{schedule_id}", json={"enabled": True})
        assert on.json()["next_run_at"] is not None
        assert on.json()["name"] == "nightly"

    async def test_change_frequency_recomputes(self, client, checklist_id):
        schedule_id = (await _create(client, checklist_id)).json()["id"]

        r = await client.put(f"/api/v1/schedules/{schedule_id}", json={"frequency": "interval", "interval_minutes": 30})

        assert r.status_code == 200
        data = r.json()
        assert data["time_of_day"] is None
        next_run = datetime.fromisoformat(data["next_run_at"])
        assert timedelta(minutes=29) < next_run - datetime.now(timezone.utc) <= timedelta(minutes=30)

    async def test_rename_keeps_next_run(self, client, checklist_id, isolated_app):
        schedule_id = (await _create(client, checklist_id, frequency="interval", interval_minutes=60)).json()["id"]
        fixed = datetime(2030, 1, 1, tzinfo=timezone.utc)
        async with isolated_app() as session:
            (await session.get(ExecutionSchedule, schedule_id)).next_run_at = fixed
            await session.commit()

        r = await client.put(f"/api/v1/schedules/{schedule_id}", json={"name": "renamed", "max_workers": 2})

        assert r.json()["name"] == "renamed"
        assert as_utc(datetime.fromisoformat(r.json()["next_run_at"])) == fixed

    async def test_reenable_clears_skip_reason(self, client, checklist_id, isolated_app):
        schedule_id = (await _create(client, checklist_id)).json()["id"]
        async with isolated_app() as session:
            (await session.get(ExecutionSchedule, schedule_id)).last_skip_reason = "x"
            await session.commit()
        await client.put(f"/api/v1/schedules/{schedule_id}", json={"enabled": False})
        r = await client.put(f"/api/v1/schedules/{schedule_id}", json={"enabled": True})
        assert r.json()["last_skip_reason"] is None

    async def test_invalid_update_returns_400(self, client, checklist_id):
        schedule_id = (await _create(client, checklist_id)).json()["id"]
        r = await client.put(f"/api/v1/schedules/{schedule_id}", json={"frequency": "weekly"})
        assert r.status_code == 400

    async def test_update_unknown_returns_404(self, client):
        assert (await client.put("/api/v1/schedules/missing", json={"enabled": False})).status_code == 404


class TestDelete:
    async def test_delete(self, client, checklist_id):
        schedule_id = (await _create(client, checklist_id)).json()["id"]
        assert (await client.delete(f"/api/v1/schedules/{schedule_id}")).status_code == 200
        assert (await client.get("/api/v1/schedules")).json()["total"] == 0
        assert (await client.delete(f"/api/v1/schedules/{schedule_id}")).status_code == 404

    async def test_deleting_checklist_deletes_schedules(self, client, checklist_id):
        await _create(client, checklist_id)
        assert (await client.delete(f"/api/v1/checklists/{checklist_id}")).status_code == 200
        assert (await client.get("/api/v1/schedules")).json()["total"] == 0


class TestPermissions:
    async def test_viewer_can_read_but_not_write(self, client, checklist_id, viewer_headers):
        schedule_id = (await _create(client, checklist_id)).json()["id"]
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=viewer_headers) as viewer:
            assert (await viewer.get("/api/v1/schedules")).status_code == 200
            assert (await viewer.get(f"/api/v1/checklists/{checklist_id}/schedules")).status_code == 200
            assert (await viewer.post(f"/api/v1/checklists/{checklist_id}/schedules", json=DAILY)).status_code == 403
            assert (await viewer.put(f"/api/v1/schedules/{schedule_id}", json={"enabled": False})).status_code == 403
            assert (await viewer.delete(f"/api/v1/schedules/{schedule_id}")).status_code == 403

    async def test_requires_login(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            assert (await anon.get("/api/v1/schedules")).status_code == 401


class TestExecutionScheduleInfo:
    async def test_execution_and_history_show_schedule_name(self, client, checklist_id, isolated_app):
        schedule_id = (await _create(client, checklist_id)).json()["id"]
        async with isolated_app() as session:
            session.add(ExecutionRecord(id="exec-s", checklist_id=checklist_id, status="completed", schedule_id=schedule_id))
            session.add(ExecutionRecord(id="exec-gone", checklist_id=checklist_id, status="completed", schedule_id="deleted-sched"))
            session.add(ExecutionRecord(id="exec-m", checklist_id=checklist_id, status="completed"))
            await session.commit()

        detail = (await client.get("/api/v1/executions/exec-s")).json()
        assert (detail["schedule_id"], detail["schedule_name"]) == (schedule_id, "nightly")

        history = {i["id"]: i for i in (await client.get(f"/api/v1/checklists/{checklist_id}/executions")).json()["items"]}
        assert history["exec-s"]["schedule_name"] == "nightly"
        assert (history["exec-gone"]["schedule_id"], history["exec-gone"]["schedule_name"]) == ("deleted-sched", None)
        assert (history["exec-m"]["schedule_id"], history["exec-m"]["schedule_name"]) == (None, None)
