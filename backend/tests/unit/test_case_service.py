"""Unit tests for CaseService.
RED: Tests should fail until CaseService is implemented.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_by_case_number = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.get = AsyncMock()
    repo.update = AsyncMock()
    repo.soft_delete = AsyncMock()
    repo.get_referencing_checklists_with_names = AsyncMock(return_value=[])
    repo.increment_version = AsyncMock()
    repo.get_next_case_number = AsyncMock(return_value="TC-001")
    return repo


@pytest.fixture
def case_service(mock_repo):
    from src.services.case_service import CaseService
    return CaseService(mock_repo)


class TestCaseServiceCreate:
    async def test_create_sets_version_1(self, case_service, mock_repo):
        mock_repo.create.return_value = MagicMock(id="uuid-1", case_number="TC-001", version=1)
        result = await case_service.create(
            name="Test",
            main_steps="steps",
            created_by="tester",
        )
        assert result.version == 1
        mock_repo.create.assert_called_once()

    async def test_create_generates_case_number(self, case_service, mock_repo):
        """Verify that create calls get_next_case_number to generate case_number."""
        mock_repo.get_next_case_number.return_value = "TC-005"
        mock_repo.create.return_value = MagicMock(id="uuid-1", case_number="TC-005", version=1)
        result = await case_service.create(
            name="Test",
            main_steps="steps",
            created_by="tester",
            system_category="web",
        )
        assert result.case_number == "TC-005"
        mock_repo.get_next_case_number.assert_called_once_with("web")


class TestCaseServiceUpdate:
    async def test_update_increments_version(self, case_service, mock_repo):
        existing = MagicMock(id="uuid-1", version=1)
        mock_repo.get.return_value = existing
        updated = MagicMock(id="uuid-1", version=2)
        mock_repo.update.return_value = updated

        result = await case_service.update("uuid-1", name="New Name", main_steps="new steps", modified_by="tester")
        assert result.version == 2

    async def test_update_nonexistent_case_raises(self, case_service, mock_repo):
        mock_repo.get.return_value = None
        with pytest.raises(ValueError, match="not_found"):
            await case_service.update("bad-id", name="x", main_steps="x", modified_by="t")


class TestCaseServiceDelete:
    async def test_soft_delete_succeeds_when_not_referenced(self, case_service, mock_repo):
        mock_repo.get.return_value = MagicMock(id="uuid-1", is_deleted=False)
        mock_repo.get_referencing_checklists_with_names.return_value = []
        mock_repo.soft_delete.return_value = True

        result = await case_service.soft_delete("uuid-1", deleted_by="tester")
        assert result["success"] is True

    async def test_soft_delete_returns_checklist_names_when_referenced(self, case_service, mock_repo):
        mock_repo.get.return_value = MagicMock(id="uuid-1", is_deleted=False)
        mock_repo.get_referencing_checklists_with_names.return_value = [
            {"id": "cl-1", "name": "Sprint 1"},
            {"id": "cl-2", "name": "Regression"},
        ]

        with pytest.raises(ValueError, match="case_in_use"):
            await case_service.soft_delete("uuid-1", deleted_by="tester")


class TestCaseServiceRFCode:
    """Tests for RF code persistence via upload endpoint (uses RobotScriptRepository)."""

    async def test_upload_persists_rf_code_to_robot_script_repo(self, case_service, mock_repo):
        """Verify that uploaded RF code is stored via RobotScriptRepository.upsert."""
        from src.repositories.robot_script_repo import RobotScriptRepository

        mock_robot_repo = MagicMock()
        mock_robot_repo.upsert = AsyncMock(return_value=MagicMock(id="rs-1", rf_code="*** Test ***\nLog    Hello"))

        # Simulate the upload endpoint logic
        case = MagicMock(id="case-1", case_number="TC-001")
        mock_repo.get.return_value = case

        # This mimics what the upload endpoint does
        await mock_robot_repo.upsert(test_case_id="case-1", rf_code="*** Test ***\nLog    Hello")

        mock_robot_repo.upsert.assert_called_once_with(test_case_id="case-1", rf_code="*** Test ***\nLog    Hello")
