"""Unit tests for TestCaseRepository.get_next_case_number sequence seeding.

Uses a real (in-memory) SQLite database because the logic depends on
DB-level upsert/sequence-table behavior that mocks cannot verify.

Regression test for: creating a case with a prefix that already has rows
(e.g. MMA-001) but no sequence row returned a duplicate number, causing
UNIQUE constraint failure -> HTTP 500 "An unexpected error occurred".
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models.base import Base
from src.models import test_case, test_data, media_attachment, case_chat_message, robot_script  # noqa: F401  (register tables)
from src.repositories.test_case_repo import TestCaseRepository


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as sess:
        yield sess
    await engine.dispose()


async def _seed_case(session, case_number: str):
    await session.execute(
        text(
            "INSERT INTO test_cases (id, case_number, name, main_steps, created_by, version, is_deleted)"
            " VALUES (:id, :cn, 'seed', 'steps', 'tester', 1, 0)"
        ),
        {"id": f"seed-{case_number}", "cn": case_number},
    )
    await session.flush()


class TestGetNextCaseNumberSeeding:
    async def test_seeds_from_existing_rows(self, session):
        """Pre-existing MMA-001 with empty sequence table -> next is MMA-002."""
        await _seed_case(session, "MMA-001")
        repo = TestCaseRepository(session)
        assert await repo.get_next_case_number("MMA") == "MMA-002"

    async def test_fresh_prefix_starts_at_001(self, session):
        repo = TestCaseRepository(session)
        assert await repo.get_next_case_number("NEWPFX") == "NEWPFX-001"
        assert await repo.get_next_case_number("NEWPFX") == "NEWPFX-002"

    async def test_skips_non_numeric_suffixes(self, session):
        """Non-numeric suffixes (e.g. legacy hand-made numbers) must not break seeding."""
        await _seed_case(session, "MMA-001")
        await _seed_case(session, "MMA-ABC")
        repo = TestCaseRepository(session)
        assert await repo.get_next_case_number("MMA") == "MMA-002"

    async def test_prefix_with_like_wildcards_matches_literally(self, session):
        """A prefix containing %/_ must not pick up other prefixes' numbers."""
        await _seed_case(session, "AXB-009")
        await _seed_case(session, "A%B-001")
        repo = TestCaseRepository(session)
        assert await repo.get_next_case_number("A%B") == "A%B-002"

    async def test_full_create_flow_no_conflict(self, session):
        """End-to-end at repo level: generated number can actually be inserted."""
        await _seed_case(session, "MMA-001")
        repo = TestCaseRepository(session)
        number = await repo.get_next_case_number("MMA")
        case = await repo.create(
            case_number=number,
            name="MMA登入",
            main_steps="1",
            created_by="admin",
            system_category="MMA",
        )
        assert case.case_number == "MMA-002"
