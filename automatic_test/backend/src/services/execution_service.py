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
        await self._session.flush()

        if not checklist or not checklist.items:
            await self._exec_repo.update_status(record.id, status="completed", passed_count=0, failed_count=0, total_count=0)
            return record

        case_ids = [item.test_case_id for item in checklist.items]
        concurrency = max_workers if parallel_mode else 1
        await self._exec_repo.update(record.id, status="running", total_count=len(case_ids))
        await self._session.flush()

        asyncio.create_task(
            ExecutionService._execute_all_cases_bg(record.id, case_ids, concurrency)
        )
        return record

    async def run_trial(self, source_case_id: str) -> ExecutionRecord:
        record = await self._exec_repo.create_for_trial_run(source_case_id=source_case_id)
        await self._exec_repo.update(record.id, status="running", total_count=1)
        await self._session.flush()
        asyncio.create_task(
            ExecutionService._execute_trial_bg(record.id, source_case_id)
        )
        return record

    @staticmethod
    async def _execute_trial_bg(execution_id: str, source_case_id: str) -> None:
        from src.core.config import get_settings
        from src.repositories.test_case_repo import TestCaseRepository
        from src.execution.listener import get_execution_queue, clear_execution_queue

        settings = get_settings()
        queue = get_execution_queue(execution_id)

        async with AsyncSessionLocal() as session:
            case_repo = TestCaseRepository(session)
            case = await case_repo.get(source_case_id)

        if not case:
            queue.put_nowait({"event": "execution_error", "execution_id": execution_id, "message": "案例不存在", "__done__": True})
            async with AsyncSessionLocal() as session:
                await ExecutionRepository(session).update_status(execution_id, status="error")
                await session.commit()
            return

        case_number = case.case_number
        robot_code: Optional[str] = None
        script_path = os.path.join(settings.robot_scripts_dir, f"{case_number}.robot")
        if os.path.exists(script_path):
            with open(script_path, "r", encoding="utf-8") as f:
                robot_code = f.read()

        queue.put_nowait({"event": "case_started", "execution_id": execution_id, "case_id": source_case_id, "case_number": case_number})

        result = await ExecutionService._run_single_case_with_timeout(
            case_id=source_case_id, robot_code=robot_code, timeout_sec=60, execution_id=execution_id
        )

        case_status = result.get("status", "error")
        passed = 1 if case_status == "passed" else 0
        failed = 0 if case_status == "passed" else 1

        queue.put_nowait({
            "event": "case_completed",
            "execution_id": execution_id,
            "case_id": source_case_id,
            "case_number": case_number,
            "status": case_status,
            "elapsed_ms": result.get("elapsed_ms", 0),
            "message": result.get("failure_message") or "",
        })

        final_status = "completed" if case_status == "passed" else "failed"
        queue.put_nowait({
            "event": "execution_completed",
            "execution_id": execution_id,
            "status": final_status,
            "passed": passed,
            "failed": failed,
            "total": 1,
            "report_url": f"/api/v1/executions/{execution_id}/results",
            "__done__": True,
        })

        async with AsyncSessionLocal() as session:
            from src.models.case_result import CaseResult
            from src.models.base import generate_uuid
            cr = CaseResult(
                id=generate_uuid(),
                execution_id=execution_id,
                test_case_id=source_case_id,
                case_version=1,
                status=case_status,
                elapsed_ms=result.get("elapsed_ms", 0),
                failure_message=result.get("failure_message"),
                position=0,
            )
            session.add(cr)
            await ExecutionRepository(session).update_status(
                execution_id, status=final_status, passed_count=passed, failed_count=failed, total_count=1
            )
            await session.commit()

        await asyncio.sleep(5)
        clear_execution_queue(execution_id)

    @staticmethod
    async def _execute_all_cases_bg(execution_id: str, case_ids: list[str], max_workers: int) -> None:
        from src.core.config import get_settings
        from src.repositories.test_case_repo import TestCaseRepository
        from src.execution.listener import get_execution_queue, clear_execution_queue

        settings = get_settings()
        queue = get_execution_queue(execution_id)

        async with AsyncSessionLocal() as session:
            case_repo = TestCaseRepository(session)
            case_number_map: dict[str, str] = {}
            for cid in case_ids:
                case = await case_repo.get(cid)
                if case:
                    case_number_map[cid] = case.case_number

        use_pabot = max_workers > 1 and len(case_ids) > 1

        try:
            if use_pabot:
                passed, failed, total = await ExecutionService._run_pabot(
                    execution_id, case_ids, case_number_map, max_workers, settings, queue
                )
            else:
                passed, failed, total = await ExecutionService._run_sequential(
                    execution_id, case_ids, case_number_map, settings, queue
                )
        except Exception as exc:
            queue.put_nowait({"event": "execution_error", "execution_id": execution_id, "message": str(exc), "__done__": True})
            async with AsyncSessionLocal() as session:
                exec_repo = ExecutionRepository(session)
                await exec_repo.update_status(execution_id, status="error")
                await session.commit()
            return

        final_status = "completed" if failed == 0 else "failed"
        queue.put_nowait({
            "event": "execution_completed",
            "execution_id": execution_id,
            "status": final_status,
            "passed": passed,
            "failed": failed,
            "total": total,
            "report_url": f"/api/v1/executions/{execution_id}/results",
            "__done__": True,
        })

        async with AsyncSessionLocal() as session:
            exec_repo = ExecutionRepository(session)
            await exec_repo.update_status(
                execution_id,
                status=final_status,
                passed_count=passed,
                failed_count=failed,
                total_count=total,
            )
            await session.commit()

        # Clean up queue after a short delay to allow SSE to drain it
        await asyncio.sleep(5)
        clear_execution_queue(execution_id)

    @staticmethod
    async def _run_sequential(
        execution_id: str,
        case_ids: list[str],
        case_number_map: dict[str, str],
        settings,
        queue: asyncio.Queue,
    ) -> tuple[int, int, int]:
        passed = 0
        failed = 0

        for idx, case_id in enumerate(case_ids):
            case_number = case_number_map.get(case_id)
            queue.put_nowait({
                "event": "case_started",
                "execution_id": execution_id,
                "case_id": case_id,
                "case_number": case_number or "",
            })

            robot_code: Optional[str] = None
            if case_number:
                script_path = os.path.join(settings.robot_scripts_dir, f"{case_number}.robot")
                if os.path.exists(script_path):
                    with open(script_path, "r", encoding="utf-8") as f:
                        robot_code = f.read()

            result = await ExecutionService._run_single_case_with_timeout(
                case_id=case_id,
                robot_code=robot_code,
                timeout_sec=300,
            )

            case_status = result.get("status", "error")
            if case_status == "passed":
                passed += 1
            else:
                failed += 1

            async with AsyncSessionLocal() as session:
                from src.models.case_result import CaseResult
                from src.models.base import generate_uuid
                cr = CaseResult(
                    id=generate_uuid(),
                    execution_id=execution_id,
                    test_case_id=case_id,
                    case_version=1,
                    status=case_status,
                    elapsed_ms=result.get("elapsed_ms", 0),
                    failure_message=result.get("failure_message"),
                    position=idx,
                )
                session.add(cr)
                await session.commit()

            queue.put_nowait({
                "event": "case_completed",
                "execution_id": execution_id,
                "case_id": case_id,
                "case_number": case_number or "",
                "status": case_status,
                "elapsed_ms": result.get("elapsed_ms", 0),
                "message": result.get("failure_message") or "",
            })

        return passed, failed, len(case_ids)

    @staticmethod
    async def _run_pabot(
        execution_id: str,
        case_ids: list[str],
        case_number_map: dict[str, str],
        max_workers: int,
        settings,
        queue: asyncio.Queue,
    ) -> tuple[int, int, int]:
        robot_files: list[str] = []
        case_number_to_id: dict[str, str] = {v: k for k, v in case_number_map.items()}

        for cid in case_ids:
            case_number = case_number_map.get(cid)
            if case_number:
                script_path = os.path.join(settings.robot_scripts_dir, f"{case_number}.robot")
                if os.path.exists(script_path):
                    robot_files.append(script_path)

        if not robot_files:
            return 0, len(case_ids), len(case_ids)

        queue.put_nowait({
            "event": "pabot_started",
            "execution_id": execution_id,
            "total": len(robot_files),
            "processes": max_workers,
        })

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = os.path.join(tmp_dir, "results")
            os.makedirs(output_dir, exist_ok=True)
            output_xml = os.path.join(output_dir, "output.xml")

            cmd = [
                "python", "-m", "pabot",
                "--processes", str(max_workers),
                "--outputdir", output_dir,
                "--output", "output.xml",
                "--nostatusrc",
            ] + robot_files

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=600)

            if not os.path.exists(output_xml):
                # pabot may have written partial output; try alternate location
                for fname in os.listdir(output_dir):
                    if fname == "output.xml":
                        output_xml = os.path.join(output_dir, fname)
                        break

            passed = 0
            failed = 0

            if os.path.exists(output_xml):
                from src.services.report_service import ReportService
                with open(output_xml, "r", encoding="utf-8") as f:
                    xml_content = f.read()

                report = ReportService()
                per_test = report.parse_per_test_results(xml_content)

                cr_rows: list[dict] = []
                for idx, test_result in enumerate(per_test):
                    cn = test_result["case_number"]
                    cid = case_number_to_id.get(cn, "")
                    status = test_result["status"]
                    if status == "passed":
                        passed += 1
                    else:
                        failed += 1
                    if cid:
                        cr_rows.append({
                            "test_case_id": cid,
                            "status": status,
                            "elapsed_ms": test_result.get("elapsed_ms", 0),
                            "failure_message": test_result.get("failure_message"),
                            "position": idx,
                        })
                    queue.put_nowait({
                        "event": "case_completed",
                        "execution_id": execution_id,
                        "case_id": cid,
                        "case_number": cn,
                        "status": status,
                        "elapsed_ms": test_result.get("elapsed_ms", 0),
                        "message": test_result.get("failure_message") or "",
                    })

                if cr_rows:
                    async with AsyncSessionLocal() as session:
                        from src.models.case_result import CaseResult
                        from src.models.base import generate_uuid
                        for row in cr_rows:
                            session.add(CaseResult(
                                id=generate_uuid(),
                                execution_id=execution_id,
                                case_version=1,
                                **row,
                            ))
                        await session.commit()

                skipped = len(case_ids) - len(per_test)
                failed += skipped
            else:
                stderr_text = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
                failed = len(robot_files)
                queue.put_nowait({
                    "event": "pabot_error",
                    "execution_id": execution_id,
                    "message": f"pabot 執行失敗：{stderr_text[:200]}",
                })

            # Persist RF native reports before tempdir is deleted
            import shutil as _shutil
            report_dest = os.path.join(settings.execution_reports_dir, execution_id)
            if os.path.isdir(output_dir):
                _shutil.copytree(output_dir, report_dest, dirs_exist_ok=True)

        return passed, failed, len(case_ids)

    @staticmethod
    async def _run_single_case_with_timeout(
        case_id: str,
        robot_code: Optional[str],
        timeout_sec: float,
        execution_id: Optional[str] = None,
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
            except asyncio.TimeoutError:
                return {"status": "timeout", "elapsed_ms": int(timeout_sec * 1000), "failure_message": "Execution timed out"}

            if execution_id:
                import shutil as _shutil
                from src.core.config import get_settings as _get_settings
                _settings = _get_settings()
                report_dest = os.path.join(_settings.execution_reports_dir, execution_id)
                _shutil.copytree(tmp_dir, report_dest, dirs_exist_ok=True)

            return result

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
