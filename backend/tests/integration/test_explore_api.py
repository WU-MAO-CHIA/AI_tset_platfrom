"""Integration tests for explore-page endpoints.

Isolated in-memory DB (get_db override); the real agent is stubbed at the
session-store boundary so no browser or LLM is launched.
"""

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
        await session.execute(text(
            "INSERT INTO users (id, username, hashed_password, role, is_active, created_at)"
            " VALUES ('u-1', 'explore_tester', 'x', 'editor', 1, CURRENT_TIMESTAMP)"
        ))
        await session.execute(text(
            "INSERT INTO test_cases (id, case_number, name, main_steps, created_by, version, is_deleted)"
            " VALUES ('case-1', 'EXP-001', 'login', '1', 'explore_tester', 1, 0)"
        ))
        await session.execute(text(
            "INSERT INTO test_data (id, test_case_id, field_name, rf_variable, field_value, source)"
            " VALUES ('td-1', 'case-1', '使用者代碼', '${USERNAME}', 'markwu', 'manual')"
        ))
        await session.execute(text(
            "INSERT INTO test_data (id, test_case_id, field_name, rf_variable, field_value, source)"
            " VALUES ('td-2', 'case-1', '網路密碼', '${PASSWORD}', 's3cr3t', 'manual')"
        ))
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
def editor_headers():
    token = create_access_token(sub="explore_tester", role="editor")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def stub_launch(monkeypatch):
    """Stub the session launcher; capture what the endpoint passes in."""
    calls: dict = {}

    def fake_launch(**kwargs):
        calls.update(kwargs)
        return {"session_id": "sess-1", "case_id": kwargs["case_id"]}

    monkeypatch.setattr(
        "src.services.explore_session_store.launch_explore_session", fake_launch
    )
    return calls


class TestExplorePage:
    async def test_launch_returns_202_and_resolves_credentials(
        self, client, editor_headers, stub_launch
    ):
        resp = await client.post(
            "/api/v1/cases/case-1/explore-page",
            json={"url": "https://example.com/login",
                  "goals": ["登入按鈕"],
                  "variables": ["${USERNAME}", "${PASSWORD}", "${NOPE}"]},
            headers=editor_headers,
        )
        assert resp.status_code == 202, resp.text[:300]
        assert resp.json()["session_id"] == "sess-1"
        assert "/explore-sessions/sess-1" in resp.json()["status_url"]
        # Only resolvable vars with values are passed; values stay server-side
        assert stub_launch["credentials"] == {"USERNAME": "markwu", "PASSWORD": "s3cr3t"}
        assert stub_launch["url"] == "https://example.com/login"
        assert stub_launch["goals"] == ["登入按鈕"]

    async def test_empty_goals_returns_422(self, client, editor_headers, stub_launch):
        resp = await client.post(
            "/api/v1/cases/case-1/explore-page",
            json={"url": "https://example.com/", "goals": []},
            headers=editor_headers,
        )
        assert resp.status_code == 422
        assert stub_launch == {}

    async def test_bad_url_returns_422(self, client, editor_headers, stub_launch):
        resp = await client.post(
            "/api/v1/cases/case-1/explore-page",
            json={"url": "ftp://example.com/x", "goals": ["按鈕"]},
            headers=editor_headers,
        )
        assert resp.status_code == 422
        assert stub_launch == {}

    async def test_nonexistent_case_returns_404(self, client, editor_headers, stub_launch):
        resp = await client.post(
            "/api/v1/cases/does-not-exist/explore-page",
            json={"url": "https://example.com/", "goals": ["按鈕"]},
            headers=editor_headers,
        )
        assert resp.status_code == 404
        assert stub_launch == {}

    async def test_max_steps_zero_returns_422(self, client, editor_headers, stub_launch):
        resp = await client.post(
            "/api/v1/cases/case-1/explore-page",
            json={"url": "https://example.com/", "goals": ["按鈕"], "max_steps": 0},
            headers=editor_headers,
        )
        assert resp.status_code == 422
        assert stub_launch == {}


class TestExploreSessionPoll:
    async def test_unknown_session_returns_404(self, client, editor_headers):
        resp = await client.get(
            "/api/v1/cases/case-1/explore-sessions/nope", headers=editor_headers
        )
        assert resp.status_code == 404

    async def test_wrong_case_returns_404(self, client, editor_headers, stub_launch):
        from src.services import explore_session_store as store

        session = store.create_session("other-case", "https://example.com/", ["x"])
        try:
            resp = await client.get(
                f"/api/v1/cases/case-1/explore-sessions/{session['session_id']}",
                headers=editor_headers,
            )
            assert resp.status_code == 404
        finally:
            store._sessions.pop(session["session_id"], None)
