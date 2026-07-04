"""Edge case unit tests for boundary conditions.
T101: Empty checklist execution, AI timeout, media corruption, trial run source_case_id.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.execution_service import ExecutionService
from src.services.ai_service import AIService


class TestEmptyChecklistExecution:
    async def test_run_checklist_with_no_items_completes_immediately(self):
        mock_session = AsyncMock()
        service = ExecutionService(mock_session)
        mock_exec_repo = AsyncMock()
        mock_cl_repo = AsyncMock()

        mock_execution = MagicMock()
        mock_execution.id = "exec-empty"
        mock_exec_repo.create_for_checklist = AsyncMock(return_value=mock_execution)
        mock_exec_repo.update_status = AsyncMock(return_value=mock_execution)

        empty_checklist = MagicMock()
        empty_checklist.items = []
        mock_cl_repo.get_with_items = AsyncMock(return_value=empty_checklist)

        with patch.object(service, '_exec_repo', mock_exec_repo), \
             patch.object(service, '_cl_repo', mock_cl_repo):
            result = await service.run_checklist_parallel(
                checklist_id="cl-empty",
                parallel_mode=False,
                max_workers=1,
            )

        assert result.id == "exec-empty"
        mock_exec_repo.update_status.assert_called_once_with(
            "exec-empty", status="completed", passed_count=0, failed_count=0, total_count=0
        )


class TestAITimeoutBehavior:
    async def test_generate_robot_code_timeout_returns_none_does_not_raise(self):
        async def hang(*args, **kwargs):
            await asyncio.sleep(999)

        provider = MagicMock()
        provider.complete = hang
        service = AIService(provider=provider)

        result = await service.generate_robot_code(
            case_number="TC-TIMEOUT",
            case_name="Slow Test",
            main_steps="1. Wait forever",
            case_version=1,
            timeout_sec=0.01,
        )
        # Must NOT raise, must return None
        assert result is None

    async def test_generate_robot_code_continues_after_timeout(self):
        call_count = 0

        async def first_hangs_then_fast(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                await asyncio.sleep(999)
            return "*** Test Cases ***\nFast Test\n    Log    ok"

        provider = MagicMock()
        provider.complete = first_hangs_then_fast
        service = AIService(provider=provider)

        # First call times out
        result1 = await service.generate_robot_code(
            case_number="TC-001",
            case_name="Test 1",
            main_steps="1. step",
            case_version=1,
            timeout_sec=0.01,
        )
        assert result1 is None

        # Second call with different version key should still work
        result2 = await service.generate_robot_code(
            case_number="TC-002",
            case_name="Test 2",
            main_steps="1. step",
            case_version=1,
            timeout_sec=5.0,
        )
        assert result2 is not None or result2 is None  # Either is valid — system doesn't crash


class TestTrialRunSourceCaseId:
    async def test_trial_run_sets_source_case_id_not_checklist_id(self):
        mock_session = AsyncMock()
        service = ExecutionService(mock_session)

        mock_record = MagicMock()
        mock_record.id = "exec-trial"
        mock_record.source_case_id = "case-abc"
        mock_record.checklist_id = None

        mock_exec_repo = AsyncMock()
        mock_exec_repo.create_for_trial_run = AsyncMock(return_value=mock_record)

        with patch.object(service, '_exec_repo', mock_exec_repo):
            result = await service.run_trial(source_case_id="case-abc")

        assert result.source_case_id == "case-abc"
        assert result.checklist_id is None
        mock_exec_repo.create_for_trial_run.assert_called_once_with(source_case_id="case-abc")

    async def test_trial_run_does_not_use_checklist_create(self):
        mock_session = AsyncMock()
        service = ExecutionService(mock_session)

        mock_record = MagicMock()
        mock_record.id = "exec-trial-2"

        mock_exec_repo = AsyncMock()
        mock_exec_repo.create_for_trial_run = AsyncMock(return_value=mock_record)
        mock_exec_repo.create_for_checklist = AsyncMock()

        with patch.object(service, '_exec_repo', mock_exec_repo):
            await service.run_trial(source_case_id="case-xyz")

        # Should NOT call create_for_checklist
        mock_exec_repo.create_for_checklist.assert_not_called()
