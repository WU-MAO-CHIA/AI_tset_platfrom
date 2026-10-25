"""Unit tests for ExecutionService.
RED: Tests should fail until the service is implemented.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.execution_service import ExecutionService


@pytest.fixture
def mock_db():
    session = AsyncMock()
    # 排入佇列時會查詢排隊中的執行（spec 003）；回傳同步的 result 物件
    session.execute.return_value = MagicMock()
    return session


class TestParallelControl:
    async def test_max_workers_clamped_to_configured_limit(self, mock_db):
        from src.core.config import get_settings

        service = ExecutionService(mock_db)
        mock_cl_repo = AsyncMock()
        mock_cl_repo.get_with_items = AsyncMock(return_value=MagicMock(items=[]))
        mock_exec_repo = AsyncMock()
        mock_exec_repo.create_for_checklist = AsyncMock(return_value=MagicMock(id="exec-1"))
        limit = get_settings().parallel_max_workers

        with patch.object(service, "_exec_repo", mock_exec_repo), \
             patch.object(service, "_cl_repo", mock_cl_repo):
            for requested, expected in ((999, limit), (limit, limit), (1, 1), (0, 1), (-3, 1)):
                await service.run_checklist_parallel("cl-001", parallel_mode=True, max_workers=requested)
                assert mock_exec_repo.create_for_checklist.call_args.kwargs["max_workers"] == expected

    async def test_run_checklist_parallel_creates_execution_record(self, mock_db):
        service = ExecutionService(mock_db)
        mock_cl_repo = AsyncMock()
        mock_exec_repo = AsyncMock()
        mock_execution = MagicMock()
        mock_execution.id = "exec-123"
        mock_exec_repo.create_for_checklist = AsyncMock(return_value=mock_execution)

        with patch.object(service, '_exec_repo', mock_exec_repo), \
             patch.object(service, '_cl_repo', mock_cl_repo):
            mock_cl_repo.get_with_items = AsyncMock(return_value=MagicMock(items=[]))
            result = await service.run_checklist_parallel(
                checklist_id="cl-001",
                parallel_mode=False,
                max_workers=1,
            )
            assert result.id == "exec-123"
            mock_exec_repo.create_for_checklist.assert_called_once_with(
                checklist_id="cl-001",
                parallel_mode=False,
                max_workers=1,
                schedule_id=None,
            )


class TestTrialRun:
    async def test_trial_run_sets_source_case_id(self, mock_db):
        service = ExecutionService(mock_db)
        mock_exec_repo = AsyncMock()
        mock_execution = MagicMock()
        mock_execution.id = "exec-trial-001"
        mock_execution.source_case_id = "case-001"
        mock_execution.checklist_id = None
        mock_exec_repo.create_for_trial_run = AsyncMock(return_value=mock_execution)

        with patch.object(service, '_exec_repo', mock_exec_repo):
            result = await service.run_trial(source_case_id="case-001")

        assert result.source_case_id == "case-001"
        assert result.checklist_id is None
        mock_exec_repo.create_for_trial_run.assert_called_once_with(source_case_id="case-001")


class TestTimeoutHandling:
    async def test_run_single_case_handles_timeout(self, mock_db):
        service = ExecutionService(mock_db)
        # run_single_case should return a "timeout" status result when RF takes too long
        result = await service._run_single_case_with_timeout(
            case_id="case-timeout",
            robot_code="*** Test Cases ***\nSlow Test\n    Sleep    1000",
            timeout_sec=0.01,
        )
        assert result["status"] in ("timeout", "failed", "error")

    async def test_run_single_case_marks_unable_when_no_code(self, mock_db):
        service = ExecutionService(mock_db)
        result = await service._run_single_case_with_timeout(
            case_id="case-no-code",
            robot_code=None,
            timeout_sec=10,
        )
        assert result["status"] in ("skipped", "failed", "error")
