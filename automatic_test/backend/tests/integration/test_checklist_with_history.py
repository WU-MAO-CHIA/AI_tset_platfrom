"""Integration tests for checklist management with execution history.
RED: Tests should fail until the models and repositories are fully implemented.
"""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.models.base import Base
from src.models.test_case import TestCase  # noqa: F401
from src.models.test_data import TestData  # noqa: F401
from src.models.media_attachment import MediaAttachment  # noqa: F401
from src.models.test_checklist import TestChecklist  # noqa: F401
from src.models.checklist_item import ChecklistItem  # noqa: F401
from src.models.execution_record import ExecutionRecord  # noqa: F401
from src.repositories.test_case_repo import TestCaseRepository
from src.repositories.checklist_repo import ChecklistRepository
from src.repositories.execution_repo import ExecutionRepository


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.fixture
async def seed_case(session: AsyncSession):
    repo = TestCaseRepository(session)
    case = await repo.create(
        case_number="CL-INT-001",
        name="Login Test",
        main_steps="1. Open browser\n2. Enter credentials\n3. Click login",
        created_by="tester",
    )
    return case


class TestChecklistCRUD:
    async def test_create_checklist_and_add_item(self, session: AsyncSession, seed_case):
        repo = ChecklistRepository(session)
        checklist = await repo.create(
            name="Sprint 1 Checklist",
            created_by="tester",
            case_ids=[seed_case.id],
        )
        assert checklist.id is not None
        assert checklist.name == "Sprint 1 Checklist"

        detail = await repo.get_with_items(checklist.id)
        assert detail is not None
        assert len(detail.items) == 1
        assert detail.items[0].test_case_id == seed_case.id

    async def test_update_items_replaces_list(self, session: AsyncSession, seed_case):
        repo = ChecklistRepository(session)
        checklist = await repo.create(
            name="Update Test",
            created_by="tester",
            case_ids=[seed_case.id],
        )

        # Remove the case
        await repo.update_items(checklist.id, case_ids=[])
        detail = await repo.get_with_items(checklist.id)
        assert len(detail.items) == 0

    async def test_get_nonexistent_checklist_returns_none(self, session: AsyncSession):
        repo = ChecklistRepository(session)
        result = await repo.get_with_items("nonexistent-id")
        assert result is None


class TestExecutionHistory:
    async def test_create_execution_record_for_checklist(self, session: AsyncSession, seed_case):
        case_repo = TestCaseRepository(session)
        cl_repo = ChecklistRepository(session)
        exec_repo = ExecutionRepository(session)

        checklist = await cl_repo.create(
            name="Exec History Test",
            created_by="tester",
            case_ids=[seed_case.id],
        )

        record = await exec_repo.create_for_checklist(
            checklist_id=checklist.id,
            parallel_mode=False,
            max_workers=1,
        )
        assert record.id is not None
        assert record.checklist_id == checklist.id
        assert record.source_case_id is None

    async def test_create_trial_run_record(self, session: AsyncSession, seed_case):
        exec_repo = ExecutionRepository(session)

        record = await exec_repo.create_for_trial_run(source_case_id=seed_case.id)
        assert record.id is not None
        assert record.source_case_id == seed_case.id
        assert record.checklist_id is None

    async def test_get_execution_history_for_checklist(self, session: AsyncSession, seed_case):
        cl_repo = ChecklistRepository(session)
        exec_repo = ExecutionRepository(session)

        checklist = await cl_repo.create(
            name="History Checklist",
            created_by="tester",
            case_ids=[seed_case.id],
        )
        await exec_repo.create_for_checklist(
            checklist_id=checklist.id,
            parallel_mode=True,
            max_workers=3,
        )

        history = await exec_repo.get_history_for_checklist(checklist.id)
        assert len(history) == 1
        assert history[0].checklist_id == checklist.id

    async def test_update_execution_status(self, session: AsyncSession, seed_case):
        cl_repo = ChecklistRepository(session)
        exec_repo = ExecutionRepository(session)

        checklist = await cl_repo.create(
            name="Status Update Test",
            created_by="tester",
            case_ids=[seed_case.id],
        )
        record = await exec_repo.create_for_checklist(
            checklist_id=checklist.id,
            parallel_mode=False,
            max_workers=1,
        )

        updated = await exec_repo.update_status(
            record.id,
            status="completed",
            passed_count=1,
            failed_count=0,
        )
        assert updated.status == "completed"
        assert updated.passed_count == 1
