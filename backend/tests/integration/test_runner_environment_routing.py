"""spec 005：清單執行依案例的執行環境分組，送到不同的 runner（兩個真的 runner/agent.py）。"""

import importlib.util
import os
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from sqlalchemy import select

from src.core.config import get_settings
from src.core.secret_box import encrypt_secret
from src.models.case_result import CaseResult
from src.models.execution_record import ExecutionRecord
from src.models.runner_environment import BUILTIN_ENVIRONMENT_ID, RunnerEnvironment
from src.models.test_case import TestCase
from src.models.test_checklist import TestChecklist
from src.services.execution_service import ExecutionService

# isolated_app 會把背景執行換成空函式，先保留真的實作
REAL_EXECUTE_ALL = ExecutionService._execute_all_cases_bg

AGENT_PATH = Path(__file__).resolve().parents[3] / "runner" / "agent.py"
PASS = "*** Test Cases ***\nT\n    Log    hi\n"


def _start_agent(token: str):
    spec = importlib.util.spec_from_file_location(f"runner_agent_{token[:4]}", AGENT_PATH)
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)
    calls: list[list[str]] = []
    real_run_job = agent.run_job

    def recording_run_job(job_spec, archive, run_as):
        calls.append(list(job_spec["tests"]))
        return real_run_job(job_spec, archive, run_as)

    agent.run_job = recording_run_job
    agent.Handler.token = token
    agent.Handler.run_as = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), agent.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}", calls


@pytest.fixture
def runners(monkeypatch):
    builtin_server, builtin_url, builtin_calls = _start_agent("a" * 40)
    other_server, other_url, other_calls = _start_agent("b" * 40)
    settings = get_settings()
    monkeypatch.setattr(settings, "execution_runner", "remote")
    monkeypatch.setattr(settings, "runner_url", builtin_url)
    monkeypatch.setattr(settings, "runner_token", "a" * 40)
    yield {"other_url": other_url, "builtin_calls": builtin_calls, "other_calls": other_calls}
    builtin_server.shutdown()
    other_server.shutdown()


async def _setup(maker, other_url, enabled=True):
    os.makedirs(get_settings().robot_scripts_dir, exist_ok=True)
    async with maker() as session:
        env = RunnerEnvironment(name="另一台", kind="linux", url=other_url,
                                token_encrypted=encrypt_secret("b" * 40), enabled=enabled)
        session.add(env)
        await session.flush()
        cases = []
        for number, env_id in (("R-001", BUILTIN_ENVIRONMENT_ID), ("R-002", env.id), ("R-003", BUILTIN_ENVIRONMENT_ID)):
            case = TestCase(case_number=number, name=number, main_steps="x", created_by="t",
                            runner_environment_id=env_id)
            session.add(case)
            cases.append(case)
            Path(get_settings().robot_scripts_dir, f"{number}.robot").write_text(PASS, encoding="utf-8")
        checklist = TestChecklist(name="CL", created_by="t")
        session.add(checklist)
        await session.flush()
        record = ExecutionRecord(execution_type="checklist", status="running", checklist_id=checklist.id)
        session.add(record)
        await session.commit()
        return env.id, [c.id for c in cases], record.id


async def _results(maker, execution_id):
    async with maker() as session:
        rows = (await session.execute(
            select(CaseResult).where(CaseResult.execution_id == execution_id).order_by(CaseResult.position)
        )).scalars().all()
        record = await session.get(ExecutionRecord, execution_id)
    return rows, record


async def test_cases_run_on_their_default_environment(isolated_app, runners):
    env_id, case_ids, execution_id = await _setup(isolated_app, runners["other_url"])

    await REAL_EXECUTE_ALL(execution_id, case_ids, 1)

    rows, record = await _results(isolated_app, execution_id)
    assert [r.test_case_id for r in rows] == case_ids  # 位置維持清單順序
    assert [r.status for r in rows] == ["passed"] * 3
    assert [r.runner_environment_name for r in rows] == ["預設容器", "另一台", "預設容器"]
    assert len(runners["builtin_calls"]) == 2 and len(runners["other_calls"]) == 1
    assert (record.status, record.passed_count, record.total_count) == ("completed", 3, 3)


async def test_override_sends_all_linux_cases_to_one_environment(isolated_app, runners):
    env_id, case_ids, execution_id = await _setup(isolated_app, runners["other_url"])

    await REAL_EXECUTE_ALL(execution_id, case_ids, 2, {"linux": env_id})

    rows, _ = await _results(isolated_app, execution_id)
    assert [r.status for r in rows] == ["passed"] * 3
    assert {r.runner_environment_id for r in rows} == {env_id}
    assert runners["builtin_calls"] == [] and len(runners["other_calls"]) == 1  # 一次 pabot


async def test_disabled_environment_marks_cases_as_error(isolated_app, runners):
    env_id, case_ids, execution_id = await _setup(isolated_app, runners["other_url"], enabled=False)

    await REAL_EXECUTE_ALL(execution_id, case_ids, 1)

    rows, record = await _results(isolated_app, execution_id)
    assert [r.status for r in rows] == ["passed", "error", "passed"]
    assert "已停用" in rows[1].failure_message
    assert runners["other_calls"] == []
    assert (record.status, record.failed_count, record.total_count) == ("failed", 1, 3)
