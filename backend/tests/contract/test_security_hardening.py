"""資安修正的回歸測試：範例金鑰、DB 連線目標、viewer 權限、token 失效、帳號鎖定、最後一個管理員。"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.core.config import Settings, get_settings
from src.core.security import create_access_token, hash_password
from src.main import app
from src.models.user import User
from src.services.db_connect_service import DBConnectionService

PASSWORD = "correct-horse-123"


def _client(headers: dict | None = None) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers or {})


async def _add_user(maker, username: str, role: str) -> None:
    async with maker() as session:
        session.add(User(username=username, hashed_password=hash_password(PASSWORD), role=role))
        await session.commit()


async def _user(maker, username: str) -> User:
    async with maker() as session:
        return (await session.execute(select(User).where(User.username == username))).scalar_one()


# ─── H1：範例金鑰 ───

def test_env_example_secret_is_treated_as_default():
    s = Settings(jwt_secret_key="change-me-to-a-strong-random-secret-key")
    assert s.is_default_secret()


def test_random_secret_is_not_default():
    assert not Settings(jwt_secret_key="a" * 64).is_default_secret()


# ─── M1：SQLite 連線不得指向平台自己的資料 ───

async def test_platform_database_is_blocked(monkeypatch, tmp_path):
    app_db = tmp_path / "data" / "autotest.db"
    monkeypatch.setattr(get_settings(), "database_url", f"sqlite+aiosqlite:///{app_db}")
    service = DBConnectionService()
    for target in (f"sqlite:///{app_db}", f"sqlite:///{app_db}-wal"):
        with pytest.raises(ValueError, match="platform's own data"):
            await service.execute_query(target, "SELECT 1")


async def test_media_dir_is_blocked():
    media = get_settings().media_root
    result = await DBConnectionService().test_connection(f"sqlite:///{media}/x.db")
    assert result["success"] is False


@pytest.mark.parametrize("conn", ["sqlite:///file:x.db?mode=ro&uri=true", "sqlite:///x.db?uri=true"])
async def test_sqlite_uri_filenames_rejected(conn):
    result = await DBConnectionService().test_connection(conn)
    assert result["success"] is False


async def test_create_connection_to_platform_db_rejected(admin_headers, monkeypatch, tmp_path):
    app_db = tmp_path / "autotest.db"
    monkeypatch.setattr(get_settings(), "database_url", f"sqlite+aiosqlite:///{app_db}")
    async with _client(admin_headers) as c:
        r = await c.post("/api/v1/db-connections", json={
            "name": "steal", "connection_string": f"sqlite:///{app_db}", "created_by": "x",
        })
    assert r.status_code == 422


async def test_unrelated_sqlite_file_still_allowed(tmp_path):
    result = await DBConnectionService().execute_query(f"sqlite:///{tmp_path / 'other.db'}", "SELECT 1 AS v")
    assert result["rows"] == [{"v": 1}]


# ─── M3：viewer 不能呼叫 AI / 匯入 ───

@pytest.mark.parametrize("path, body", [
    ("/api/v1/cases/chat-preview", {"message": "hi"}),
    ("/api/v1/cases/ai-complete", {"partial_steps": "1"}),
    ("/api/v1/cases/preview-rf", {"main_steps": "1"}),
])
async def test_viewer_cannot_call_llm_endpoints(isolated_app, path, body):
    await _add_user(isolated_app, "viewer1", "viewer")
    headers = {"Authorization": f"Bearer {create_access_token(sub='viewer1', role='viewer')}"}
    async with _client(headers) as c:
        r = await c.post(path, json=body)
    assert r.status_code == 403


# ─── L2：token 失效 ───

async def test_logout_revokes_token(admin_headers):
    async with _client(admin_headers) as c:
        assert (await c.get("/api/v1/auth/me")).status_code == 200
        assert (await c.post("/api/v1/auth/logout")).status_code == 200
        assert (await c.get("/api/v1/auth/me")).status_code == 401


async def test_logout_without_token_still_clears_cookie(isolated_app):
    async with _client() as c:
        r = await c.post("/api/v1/auth/logout")
    assert r.status_code == 200


async def test_password_reset_revokes_existing_tokens(isolated_app, admin_headers):
    await _add_user(isolated_app, "ed1", "editor")
    ed_headers = {"Authorization": f"Bearer {create_access_token(sub='ed1', role='editor')}"}
    user = await _user(isolated_app, "ed1")
    async with _client(admin_headers) as admin:
        r = await admin.put(f"/api/v1/admin/users/{user.id}", json={"new_password": "brand-new-pass-1"})
        assert r.status_code == 200
    async with _client(ed_headers) as c:
        assert (await c.get("/api/v1/auth/me")).status_code == 401


async def test_login_token_carries_current_version(isolated_app):
    await _add_user(isolated_app, "ed2", "editor")
    async with _client() as c:
        r = await c.post("/api/v1/auth/login", json={"username": "ed2", "password": PASSWORD})
        token = r.json()["access_token"]
        assert (await c.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})).status_code == 200
        r = await c.post("/api/v1/auth/login", json={"username": "ed2", "password": PASSWORD})
        new_token = r.json()["access_token"]
        assert (await c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"})).status_code == 200
        assert (await c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 401


# ─── L4：帳號鎖定 ───

async def test_account_locked_after_repeated_failures(isolated_app):
    await _add_user(isolated_app, "ed3", "editor")
    async with _client() as c:
        for _ in range(10):
            r = await c.post("/api/v1/auth/login", json={"username": "ed3", "password": "wrong-password"})
            assert r.status_code == 401
        r = await c.post("/api/v1/auth/login", json={"username": "ed3", "password": PASSWORD})
    assert r.status_code == 429


async def test_successful_login_resets_failures(isolated_app):
    await _add_user(isolated_app, "ed4", "editor")
    async with _client() as c:
        for _ in range(9):
            await c.post("/api/v1/auth/login", json={"username": "ed4", "password": "wrong-password"})
        assert (await c.post("/api/v1/auth/login", json={"username": "ed4", "password": PASSWORD})).status_code == 200
        for _ in range(9):
            await c.post("/api/v1/auth/login", json={"username": "ed4", "password": "wrong-password"})
        assert (await c.post("/api/v1/auth/login", json={"username": "ed4", "password": PASSWORD})).status_code == 200


# ─── L5：保留最後一個管理員 ───

async def test_cannot_demote_or_disable_last_admin(isolated_app, admin_headers):
    admin = await _user(isolated_app, "admin")
    async with _client(admin_headers) as c:
        assert (await c.put(f"/api/v1/admin/users/{admin.id}", json={"role": "editor"})).status_code == 400
        assert (await c.put(f"/api/v1/admin/users/{admin.id}", json={"is_active": False})).status_code == 400
    assert (await _user(isolated_app, "admin")).role == "admin"


async def test_can_demote_admin_when_another_exists(isolated_app, admin_headers):
    await _add_user(isolated_app, "admin2", "admin")
    other = await _user(isolated_app, "admin2")
    async with _client(admin_headers) as c:
        assert (await c.put(f"/api/v1/admin/users/{other.id}", json={"role": "viewer"})).status_code == 200
        assert (await c.delete(f"/api/v1/admin/users/{other.id}")).status_code == 200
