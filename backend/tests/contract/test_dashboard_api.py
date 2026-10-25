"""管理員監控儀表板 API。"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.security import create_access_token
from src.main import app
from src.models.execution_record import ExecutionRecord
from src.models.execution_schedule import ExecutionSchedule
from src.models.test_checklist import TestChecklist
from src.models.user import User

URL = "/api/v1/admin/dashboard"


@pytest.fixture
async def client(admin_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=admin_headers) as c:
        yield c


async def _seed(isolated_app):
    now = datetime.now(timezone.utc)
    checklist_id = str(uuid.uuid4())
    async with isolated_app() as session:
        session.add(TestChecklist(id=checklist_id, name="回歸清單", created_by="admin"))
        await session.flush()
        schedule = ExecutionSchedule(
            checklist_id=checklist_id, name="夜間", frequency="daily", time_of_day="02:00",
            next_run_at=now + timedelta(hours=2), created_by="admin",
        )
        soon = ExecutionSchedule(
            checklist_id=checklist_id, name="每小時", frequency="interval", interval_minutes=60,
            next_run_at=now + timedelta(minutes=10), created_by="admin",
        )
        off = ExecutionSchedule(
            checklist_id=checklist_id, name="停用", frequency="daily", time_of_day="03:00",
            enabled=False, created_by="admin",
        )
        session.add_all([schedule, soon, off])
        await session.flush()
        session.add_all([
            ExecutionRecord(checklist_id=checklist_id, status="running", started_at=now,
                            passed_count=2, failed_count=1, total_count=5, schedule_id=schedule.id),
            ExecutionRecord(id="p-late", checklist_id=checklist_id, status="pending", priority=0,
                            queued_at=now - timedelta(minutes=1)),
            ExecutionRecord(id="p-early", checklist_id=checklist_id, status="pending", priority=0,
                            queued_at=now - timedelta(minutes=5)),
            ExecutionRecord(id="p-high", checklist_id=checklist_id, status="pending", priority=10,
                            queued_at=now),
            ExecutionRecord(checklist_id=checklist_id, status="completed", finished_at=now),
        ])
        await session.commit()


async def test_dashboard_lists_running_pending_and_enabled_schedules(client, isolated_app):
    await _seed(isolated_app)

    r = await client.get(URL)

    assert r.status_code == 200
    data = r.json()
    assert data["counts"] == {"running": 1, "pending": 3, "schedules_enabled": 2, "schedules_total": 3}
    assert data["max_concurrent"] >= 1
    assert data["timezone"] == "Asia/Taipei"

    [running] = data["running"]
    assert running["target_name"] == "回歸清單"
    assert running["schedule_name"] == "夜間"
    assert (running["passed_count"], running["failed_count"], running["total_count"]) == (2, 1, 5)

    # 與 worker 領取順序一致：priority 高者優先，再依排隊時間
    assert [p["id"] for p in data["pending"]] == ["p-high", "p-early", "p-late"]

    # 只列啟用中的排程，依下次執行時間排列
    assert [s["name"] for s in data["schedules"]] == ["每小時", "夜間"]
    assert data["schedules"][0]["checklist_name"] == "回歸清單"


async def test_dashboard_empty(client):
    r = await client.get(URL)
    assert r.status_code == 200
    assert r.json()["counts"] == {"running": 0, "pending": 0, "schedules_enabled": 0, "schedules_total": 0}


@pytest.mark.parametrize("role", ["viewer", "editor"])
async def test_dashboard_admin_only(isolated_app, role):
    async with isolated_app() as session:
        session.add(User(username=f"{role}1", hashed_password="x", role=role))
        await session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(sub=f'{role}1', role=role)}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        assert (await c.get(URL)).status_code == 403


async def test_dashboard_requires_login(isolated_app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await c.get(URL)).status_code == 401
