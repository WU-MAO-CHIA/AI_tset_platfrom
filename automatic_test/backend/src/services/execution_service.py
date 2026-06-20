import asyncio
import os
import tempfile
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import AsyncSessionLocal
from src.models.execution_record import ExecutionRecord
from src.repositories.checklist_repo import ChecklistRepository
from src.repositories.execution_repo import ExecutionRepository


class ExecutionService:
    def __init__(self, session: Optional[AsyncSession]) -> None:
        self._session = session
        if session is not None:
            self._cl_repo = ChecklistRepository(session)
            self._exec_repo = ExecutionRepository(session)

    async def run_checklist_parallel(
        self,
        checklist_id: str,
        parallel_mode: bool,
        max_workers: int,
    ) -> ExecutionRecord:
        checklist = await self._cl_repo.get_with_items(checklist_id)
        record = await self._exec_repo.create_for_checklist(
            checklist_id=checklist_id,
            parallel_mode=parallel_mode,
            max_workers=max_workers,
        )
        # Flush so record.id is available before session closes
        await self._session.flush()

        if not checklist or not checklist.items:
            await self._exec_repo.update_status(record.id, status="completed", passed_count=0, failed_count=0, total_count=0)
            return record

        # Extract plain data before session is closed by request lifecycle
        case_ids = [item.test_case_id for item in checklist.items]
        concurrency = max_workers if parallel_mode else 1

        asyncio.create_task(
            ExecutionService._execute_all_cases_bg(record.id, case_ids, concurrency)
        )
        return record

    async def run_trial(self, source_case_id: str) -> ExecutionRecord:
        return await self._exec_repo.create_for_trial_run(source_case_id=source_case_id)

    @staticmethod
    async def _execute_all_cases_bg(execution_id: str, case_ids: list[str], max_workers: int) -> None:
        from src.core.config import get_settings
        from src.repositories.test_case_repo import TestCaseRepository
        settings = get_settings()

        # Fetch case_number for each case_id so we can locate the .robot file
        async with AsyncSessionLocal() as session:
            case_repo = TestCaseRepository(session)
            case_number_map: dict[str, str] = {}
            for cid in case_ids:
                case = await case_repo.get(cid)
                if case:
                    case_number_map[cid] = case.case_number

        semaphore = asyncio.Semaphore(max_workers)

        async def run_one(case_id: str) -> dict:
            async with semaphore:
                robot_code: Optional[str] = None
                case_number = case_number_map.get(case_id)
                if case_number:
                    script_path = os.path.join(settings.robot_scripts_dir, f"{case_number}.robot")
                    if os.path.exists(script_path):
                        with open(script_path, "r", encoding="utf-8") as f:
                            robot_code = f.read()
                return await ExecutionService._run_single_case_with_timeout(
                    case_id=case_id,
                    robot_code=robot_code,
                    timeout_sec=300,
                )

        tasks = [asyncio.create_task(run_one(cid)) for cid in case_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        passed = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "passed")
        failed = sum(1 for r in results if not (isinstance(r, dict) and r.get("status") == "passed"))

        async with AsyncSessionLocal() as session:
            exec_repo = ExecutionRepository(session)
            await exec_repo.update_status(
                execution_id,
                status="completed",
                passed_count=passed,
                failed_count=failed,
                total_count=len(results),
            )
            await session.commit()

    @staticmethod
    async def _run_single_case_with_timeout(
        case_id: str,
        robot_code: Optional[str],
        timeout_sec: float,
    ) -> dict:
        if robot_code is None:
            return {"status": "skipped", "elapsed_ms": 0, "failure_message": "No robot code available"}

        with tempfile.TemporaryDirectory() as tmp_dir:
            robot_file = os.path.join(tmp_dir, "test.robot")
            output_xml = os.path.join(tmp_dir, "output.xml")
            with open(robot_file, "w", encoding="utf-8") as f:
                f.write(robot_code)

            try:
                result = await asyncio.wait_for(
                    ExecutionService._execute_robot_subprocess(robot_file, output_xml, timeout_sec),
                    timeout=timeout_sec,
                )
                return result
            except asyncio.TimeoutError:
                return {"status": "timeout", "elapsed_ms": int(timeout_sec * 1000), "failure_message": "Execution timed out"}

    @staticmethod
    async def _execute_robot_subprocess(
        robot_file: str,
        output_xml: str,
        timeout_sec: float,
    ) -> dict:
        import time
        start_ms = int(time.time() * 1000)

        try:
            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "robot",
                "--outputdir", os.path.dirname(output_xml),
                "--output", output_xml,
                "--nostatusrc",
                robot_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            elapsed = int(time.time() * 1000) - start_ms
            return {"status": "timeout", "elapsed_ms": elapsed, "failure_message": "Execution timed out"}
        except Exception as exc:
            elapsed = int(time.time() * 1000) - start_ms
            return {"status": "error", "elapsed_ms": elapsed, "failure_message": str(exc)}

        elapsed = int(time.time() * 1000) - start_ms

        if not os.path.exists(output_xml):
            return {"status": "error", "elapsed_ms": elapsed, "failure_message": "output.xml not generated"}

        from src.services.report_service import ReportService
        with open(output_xml, "r", encoding="utf-8") as f:
            xml_content = f.read()

        report = ReportService()
        parsed = report.parse_xml(xml_content)
        return {
            "status": parsed["status"],
            "elapsed_ms": parsed.get("elapsed_ms", elapsed),
            "failure_message": parsed.get("failure_message"),
        }
