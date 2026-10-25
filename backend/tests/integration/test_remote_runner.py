"""EXECUTION_RUNNER=remote：試跑與 pabot 交給 runner/agent.py 執行，結果解回本機工作目錄。"""
import importlib.util
import os
import threading
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from src.core.config import get_settings
from src.execution import runner_client
from src.services.execution_service import ExecutionService, _run_robot_job

TOKEN = "r" * 40
AGENT_PATH = Path(__file__).resolve().parents[3] / "runner" / "agent.py"


@pytest.fixture
def runner(monkeypatch):
    spec = importlib.util.spec_from_file_location("runner_agent", AGENT_PATH)
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)
    agent.Handler.token = TOKEN
    agent.Handler.run_as = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), agent.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    settings = get_settings()
    monkeypatch.setattr(settings, "execution_runner", "remote")
    monkeypatch.setattr(settings, "runner_url", f"http://127.0.0.1:{server.server_address[1]}")
    monkeypatch.setattr(settings, "runner_token", TOKEN)
    yield agent
    server.shutdown()


async def test_trial_run_executes_on_runner(runner, tmp_path):
    code = "*** Test Cases ***\nRemote\n    Should Be Equal    %{AUTOTEST_API_URL}    " + get_settings().internal_api_url + "\n"
    report = tmp_path / "report"
    result = await ExecutionService._run_single_case_with_timeout("case-1", code, 60, report_dest=str(report))
    assert result["status"] == "passed", result
    assert (report / "log.html").exists() and (report / "output.xml").exists()


async def test_pabot_job_executes_on_runner(runner, tmp_path):
    (tmp_path / "robot_scripts").mkdir()
    (tmp_path / "results").mkdir()
    for name in ("A-001", "B-002"):
        (tmp_path / "robot_scripts" / f"{name}.robot").write_text("*** Test Cases ***\nT\n    Log    hi\n")
    job = await _run_robot_job(str(tmp_path), "pabot",
                               ["robot_scripts/A-001.robot", "robot_scripts/B-002.robot"], "results", 120, processes=2)
    assert not job["timed_out"]
    assert (tmp_path / "results" / "output.xml").exists()


async def test_secrets_are_not_sent_to_runner(runner, tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-leak")
    monkeypatch.setenv("RUNNER_TOKEN", TOKEN)
    code = ("*** Test Cases ***\nNo Secrets\n    Should Be Equal    %{ANTHROPIC_API_KEY=none}    none\n"
            "    Should Be Equal    %{RUNNER_TOKEN=none}    none\n")
    result = await ExecutionService._run_single_case_with_timeout("case-1", code, 60)
    assert result["status"] == "passed", result


async def test_unreachable_runner_reports_error(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "execution_runner", "remote")
    monkeypatch.setattr(settings, "runner_url", "http://127.0.0.1:1")
    result = await ExecutionService._run_single_case_with_timeout("case-1", "*** Test Cases ***\nT\n    Log    x\n", 30)
    assert result["status"] == "error"
    assert "runner" in result["failure_message"]


def test_extract_ignores_paths_outside_workdir(tmp_path):
    import io

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../escape.txt", "x")
        zf.writestr("/abs.txt", "x")
        zf.writestr("ok/output.xml", "<robot/>")
    work = tmp_path / "work"
    work.mkdir()
    runner_client._extract(buf.getvalue(), str(work))
    assert (work / "ok" / "output.xml").exists()
    assert not (tmp_path / "escape.txt").exists()
    assert not os.path.exists("/abs.txt")
