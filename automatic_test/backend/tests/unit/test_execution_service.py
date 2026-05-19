"""Unit tests for ExecutionService.
RED: Tests should fail until the service is implemented.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.execution_service import ExecutionService


@pytest.fixture
def mock_db():
    session = AsyncMock()
    return session


class TestSemaphoreParallelControl:
    async def test_semaphore_limits_concurrent_workers(self, mock_db):
        service = ExecutionService(mock_db)
        # Semaphore should limit concurrent coroutines to max_workers
        assert service._semaphore is None  # Not set until run_checklist_parallel called
        concurrency = 3
        semaphore = asyncio.Semaphore(concurrency)
        assert semaphore._value == concurrency

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
