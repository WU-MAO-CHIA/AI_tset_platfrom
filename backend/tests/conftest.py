"""共用 fixture：隔離的 app 執行環境。

`isolated_app` 讓測試改用 in-memory DB（已 seed admin/admin）、檔案寫入導向
tmp_path，且不啟動 robot 子程序、不呼叫真的 LLM——不會碰到 data/autotest.db。
contract 測試一律套用（tests/contract/conftest.py）；其他測試需要時明確引用。
"""
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import src.api.auth as auth_api
import src.api.cases as cases_api
import src.api.executions as executions_api
import src.core.database as core_db
import src.services.execution_service as execution_service
from src.core.config import get_settings
from src.core.security import create_access_token, hash_password
from src.main import app
from src.models.base import Base
from src.models.user import User

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
_ADMIN_HASH = hash_password(ADMIN_PASSWORD)  # bcrypt 很慢，只算一次


class FakeLLMProvider:
    """回傳固定內容的 LLMProvider，AI 端點照常解析回應但不對外連線。"""

    RF_CODE = "*** Test Cases ***\nFake Test\n    Log    fake"

    async def complete(self, prompt: str) -> str:
        return self.RF_CODE

    async def complete_with_vision(self, prompt: str, media_list: list) -> str:
        return self.RF_CODE

    async def complete_with_messages(self, messages: list[dict], system: str = "") -> str:
        return f"---MESSAGE---\nfake reply\n---RF_CODE---\n{self.RF_CODE}\n---END---"


async def _skip_background_run(*args, **kwargs) -> None:
    return None


@pytest.fixture
async def isolated_app(monkeypatch, tmp_path):
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        session.add(User(username=ADMIN_USERNAME, hashed_password=_ADMIN_HASH, role="admin"))
        await session.commit()

    async def override_get_db():
        async with maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[core_db.get_db] = override_get_db
    # 直接使用 session factory 的程式（背景執行、SSE 輪詢）也導向 in-memory DB
    for module in (core_db, execution_service, executions_api):
        monkeypatch.setattr(module, "AsyncSessionLocal", maker)

    settings = get_settings()
    for attr in ("media_root", "robot_scripts_dir", "execution_reports_dir"):
        monkeypatch.setattr(settings, attr, str(tmp_path / attr))

    monkeypatch.setattr(execution_service.ExecutionService, "_execute_trial_bg",
                        staticmethod(_skip_background_run))
    monkeypatch.setattr(execution_service.ExecutionService, "_execute_all_cases_bg",
                        staticmethod(_skip_background_run))
    monkeypatch.setattr(cases_api, "get_provider", lambda model_id, settings: FakeLLMProvider())
    monkeypatch.setattr(auth_api, "_LOGIN_ATTEMPTS", {})  # 登入限流每個測試重新計算

    yield maker

    app.dependency_overrides.pop(core_db.get_db, None)
    await engine.dispose()


@pytest.fixture
def admin_headers(isolated_app):
    token = create_access_token(sub=ADMIN_USERNAME, role="admin")
    return {"Authorization": f"Bearer {token}"}
