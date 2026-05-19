"""Integration tests for TestCase CRUD operations with real SQLite.
RED: Tests should fail until models, repo, and service are implemented.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base
# Import all models so SQLAlchemy can resolve relationships
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


class TestCaseCRUDIntegration:
    async def test_create_and_retrieve_case(self, session: AsyncSession):
        from src.repositories.test_case_repo import TestCaseRepository
        from src.services.case_service import CaseService

        repo = TestCaseRepository(session)
        service = CaseService(repo)

        result = await service.create(
            case_number="TC-001",
            name="Login Test",
            main_steps="1. Open page\n2. Login",
            system_category="auth",
            created_by="tester",
        )
        assert result.id is not None
        assert result.version == 1

        retrieved = await repo.get(result.id)
        assert retrieved is not None
        assert retrieved.case_number == "TC-001"

    async def test_update_increments_version(self, session: AsyncSession):
        from src.repositories.test_case_repo import TestCaseRepository
        from src.services.case_service import CaseService

        repo = TestCaseRepository(session)
        service = CaseService(repo)

        created = await service.create(
            case_number="TC-002",
            name="Original",
            main_steps="steps",
            created_by="tester",
        )
        updated = await service.update(created.id, name="Updated", main_steps="new steps", modified_by="tester")
        assert updated.version == 2

    async def test_soft_delete_hides_from_list(self, session: AsyncSession):
        from src.repositories.test_case_repo import TestCaseRepository
        from src.services.case_service import CaseService

        repo = TestCaseRepository(session)
        service = CaseService(repo)

        created = await service.create(
            case_number="TC-003",
            name="To Delete",
            main_steps="steps",
            created_by="tester",
        )
        await service.soft_delete(created.id, deleted_by="tester")

        cases, total = await repo.list_with_filters(page=1, page_size=20)
        ids = [c.id for c in cases]
        assert created.id not in ids
