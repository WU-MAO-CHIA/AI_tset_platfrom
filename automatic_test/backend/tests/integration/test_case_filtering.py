"""Integration tests for case filtering with real SQLite.
RED: Tests should fail until filtering is implemented.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models.base import Base
from src.models.test_case import TestCase  # noqa: F401
from src.models.test_data import TestData  # noqa: F401
from src.models.media_attachment import MediaAttachment  # noqa: F401
from src.models.test_checklist import TestChecklist  # noqa: F401
from src.models.checklist_item import ChecklistItem  # noqa: F401

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as s:
        yield s
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_session(session):
    from src.repositories.test_case_repo import TestCaseRepository
    from src.services.case_service import CaseService

    repo = TestCaseRepository(session)
    svc = CaseService(repo)

    await svc.create("TC-F01", "Auth Login", "steps", created_by="t", system_category="auth")
    await svc.create("TC-F02", "Auth Logout", "steps", created_by="t", system_category="auth")
    await svc.create("TC-F03", "Order Create", "steps", created_by="t", system_category="order")
    await svc.create("TC-F04", "Order Delete", "steps", created_by="t", system_category="order")
    yield session


class TestCaseFilteringIntegration:
    async def test_filter_by_system_category(self, seeded_session):
        from src.repositories.test_case_repo import TestCaseRepository
        repo = TestCaseRepository(seeded_session)
        cases, total = await repo.list_with_filters(system_category="auth")
        assert total == 2
        assert all(c.system_category == "auth" for c in cases)

    async def test_filter_by_keyword(self, seeded_session):
        from src.repositories.test_case_repo import TestCaseRepository
        repo = TestCaseRepository(seeded_session)
        cases, total = await repo.list_with_filters(keyword="Order")
        assert total == 2
        assert all("order" in c.name.lower() for c in cases)

    async def test_combined_filter(self, seeded_session):
        from src.repositories.test_case_repo import TestCaseRepository
        repo = TestCaseRepository(seeded_session)
        cases, total = await repo.list_with_filters(system_category="auth", keyword="Login")
        assert total == 1

    async def test_pagination(self, seeded_session):
        from src.repositories.test_case_repo import TestCaseRepository
        repo = TestCaseRepository(seeded_session)
        cases, total = await repo.list_with_filters(page=1, page_size=2)
        assert len(cases) == 2
        assert total == 4
