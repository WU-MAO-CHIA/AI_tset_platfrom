"""Integration tests for the SSE execution stream and trial-run guard.

Uses an isolated in-memory SQLite DB (get_db dependency override) so the
real data/autotest.db is never touched.

Regression tests for:
1. GET /executions/{id}/stream ignored the login cookie (param was bound as
   a *query* param named access_token_cookie, while login sets a cookie
   named access_token) -> every stream got 401 "Token required" ->
   frontend showed "SSE connection failed", 0/0, error badge.
2. The stream generator yielded a spurious execution_error ("執行逾時")
   from inside `finally` after EVERY cleanly finished stream.
3. Trial run with no RF code created a confusing instant-failure record
   instead of a clear 422.
"""

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.core.database import get_db
from src.core.security import create_access_token
from src.main import app
from src.models.base import Base
from src.models import (  # noqa: F401  (register all tables)
    test_case, test_data, media_attachment, test_checklist, checklist_item,
    execution_record, db_connection, automation_code, case_result,
    execution_media, case_chat_message, robot_script, user, system_category,
    app_setting,
)


@pytest.fixture
async def test_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async with maker() as session:
        # Seed an active editor user for auth
        await session.execute(
            text(
                "INSERT INTO users (id, username, hashed_password, role, is_active, created_at)"
                " VALUES ('u-1', 'stream_tester', 'x', 'editor', 1, CURRENT_TIMESTAMP)"
            )
        )
        # Seed a test case (trial-run target)
        await session.execute(
            text(
                "INSERT INTO test_cases (id, case_number, name, main_steps, created_by, version, is_deleted)"
                " VALUES ('case-1', 'ZZZTEST-001', 'stream case', '1', 'stream_tester', 1, 0)"
            )
        )
        # Seed an already-terminal execution record (finite stream)
        await session.execute(
            text(
                "INSERT INTO execution_records (id, source_case_id, execution_type, status,"
                " parallel_mode, max_workers, passed_count, failed_count, total_count)"
                " VALUES ('exec-1', 'case-1', 'trial', 'error', 0, 1, 0, 1, 1)"
            )
        )
        await session.commit()

    async def override_get_db():
        async with maker() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = override_get_db
    yield maker
    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


@pytest.fixture
def token():
    return create_access_token(sub="stream_tester", role="editor")


@pytest.fixture
async def client(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class TestStreamAuth:
    async def test_stream_without_token_returns_401(self, client):
        resp = await client.get("/api/v1/executions/exec-1/stream")
        assert resp.status_code == 401

    async def test_stream_with_login_cookie_returns_events(self, client, token):
        """Cookie named access_token (as set by login) must be accepted."""
        client.cookies.set("access_token", token)
        resp = await client.get("/api/v1/executions/exec-1/stream")
        assert resp.status_code == 200, resp.text[:300]
        body = resp.text
        assert "execution_started" in body
        assert "execution_completed" in body

    async def test_stream_has_no_spurious_timeout_error(self, client, token):
        """A cleanly finished stream must NOT end with execution_error 執行逾時."""
        client.cookies.set("access_token", token)
        resp = await client.get("/api/v1/executions/exec-1/stream")
        assert resp.status_code == 200
        assert "執行逾時" not in resp.text
        assert "execution_error" not in resp.text

    async def test_stream_with_query_token_still_works(self, client, token):
        resp = await client.get(f"/api/v1/executions/exec-1/stream?token={token}")
        assert resp.status_code == 200


class TestTrialRunGuard:
    async def test_trial_run_without_rf_code_returns_422(self, client, token):
        from src.core.config import get_settings

        script_path = os.path.join(get_settings().robot_scripts_dir, "ZZZTEST-001.robot")
        assert not os.path.exists(script_path), "test precondition: no robot file"
        resp = await client.post(
            "/api/v1/cases/case-1/trial-run",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422, resp.text[:300]
        assert resp.json()["detail"]["error"] == "no_robot_code"

    async def test_trial_run_with_db_code_is_accepted(self, client, token, test_db):
        """DB-sourced RF code satisfies the guard even without a disk file."""
        async with test_db() as session:
            from sqlalchemy import text as _text
            await session.execute(_text(
                "INSERT INTO robot_scripts (id, test_case_id, rf_code)"
                " VALUES ('rs-1', 'case-1', '*** Test Cases ***')"
            ))
            await session.commit()
        resp = await client.post(
            "/api/v1/cases/case-1/trial-run",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 202, resp.text[:300]
        assert "execution_id" in resp.json()

    async def test_trial_run_nonexistent_case_returns_404(self, client, token):
        resp = await client.post(
            "/api/v1/cases/does-not-exist/trial-run",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestRfReportStatus:
    async def test_missing_report_returns_unavailable(self, client, token):
        resp = await client.get(
            "/api/v1/executions/exec-1/rf-report-status",
            params={"filename": "report.html"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"available": False}

    async def test_existing_report_returns_available(self, client, token):
        from src.core.config import get_settings

        report_dir = os.path.join(get_settings().execution_reports_dir, "exec-1")
        os.makedirs(report_dir, exist_ok=True)
        marker = os.path.join(report_dir, "report.html")
        try:
            with open(marker, "w", encoding="utf-8") as f:
                f.write("<html></html>")
            resp = await client.get(
                "/api/v1/executions/exec-1/rf-report-status",
                params={"filename": "report.html"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert resp.json() == {"available": True}
        finally:
            if os.path.exists(marker):
                os.remove(marker)

    async def test_nonexistent_execution_returns_404(self, client, token):
        resp = await client.get(
            "/api/v1/executions/does-not-exist/rf-report-status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


def _uid() -> str:
    return uuid.uuid4().hex
