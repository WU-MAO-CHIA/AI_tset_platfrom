"""runner agent：只接受 robot / pabot、路徑不可跳出工作目錄、環境變數不能覆寫、需要 token。"""
import io
import json
import os
import sys
import threading
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import agent  # noqa: E402

TOKEN = "t" * 40
PASS_ROBOT = "*** Test Cases ***\nPass\n    Log    hello\n"


def _zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


class TestBuildArgv:
    def test_robot(self):
        argv, timeout = agent.build_argv({"tool": "robot", "tests": ["robot_scripts/t.robot"], "timeout": 30}, "py")
        assert argv == ["py", "-m", "robot", "--outputdir", ".", "--output", "output.xml", "--nostatusrc",
                        "robot_scripts/t.robot"]
        assert timeout == 30

    def test_pabot_caps_processes_and_timeout(self):
        argv, timeout = agent.build_argv({"tool": "pabot", "tests": ["a.robot"], "outputdir": "results",
                                          "processes": 999, "timeout": 99999}, "py")
        assert argv[:5] == ["py", "-m", "pabot.pabot", "--processes", str(agent.MAX_PROCESSES)]
        assert argv[5:7] == ["--outputdir", "results"]
        assert timeout == agent.MAX_TIMEOUT_SEC

    @pytest.mark.parametrize("spec", [
        {"tool": "sh", "tests": ["a.robot"]},
        {"tool": "robot", "tests": []},
        {"tool": "robot", "tests": ["../etc/passwd"]},
        {"tool": "robot", "tests": ["/etc/passwd"]},
        {"tool": "robot", "tests": ["a.robot"], "outputdir": "../out"},
        {"tool": "robot", "tests": ["--listener=evil"], "outputdir": "/tmp"},
    ])
    def test_rejects_bad_specs(self, spec):
        with pytest.raises(agent.JobError):
            agent.build_argv(spec, "py")


def test_env_cannot_override_protected_keys():
    env = agent.build_env({"PATH": "/evil", "LD_PRELOAD": "x.so", "PYTHONPATH": "/evil", "RUNNER_TOKEN": "x",
                           "AUTOTEST_CAPTCHA_TOKEN": "cap", "MY_VAR": "1"}, "/home/runner")
    assert env["PATH"] != "/evil" and env["HOME"] == "/home/runner"
    assert "LD_PRELOAD" not in env and "RUNNER_TOKEN" not in env and env.get("PYTHONPATH") is None
    assert env["AUTOTEST_CAPTCHA_TOKEN"] == "cap" and env["MY_VAR"] == "1"


def test_extract_rejects_path_traversal(tmp_path):
    with pytest.raises(agent.JobError):
        agent._safe_extract(_zip({"../escape.txt": "x"}), str(tmp_path))
    assert not (tmp_path.parent / "escape.txt").exists()


def test_run_job_returns_outputs():
    result, archive = agent.run_job({"tool": "robot", "tests": ["robot_scripts/t.robot"], "timeout": 60},
                                    _zip({"robot_scripts/t.robot": PASS_ROBOT}), run_as="")
    assert result["returncode"] == 0 and not result["timed_out"]
    names = zipfile.ZipFile(io.BytesIO(archive)).namelist()
    assert "output.xml" in names and "log.html" in names


def test_run_job_timeout_kills_process():
    result, _ = agent.run_job({"tool": "robot", "tests": ["s.robot"], "timeout": 2},
                              _zip({"s.robot": "*** Test Cases ***\nS\n    Sleep    60s\n"}), run_as="")
    assert result["timed_out"] and result["elapsed_ms"] < 15000


@pytest.fixture
def server():
    agent.Handler.token = TOKEN
    agent.Handler.run_as = ""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), agent.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _post(url, token, spec, body):
    req = urllib.request.Request(f"{url}/run", data=body, method="POST", headers={
        "Authorization": f"Bearer {token}", "X-Runner-Spec": json.dumps(spec), "Content-Type": "application/zip"})
    return urllib.request.urlopen(req, timeout=60)


def test_http_requires_token(server):
    with pytest.raises(urllib.error.HTTPError) as exc:
        _post(server, "wrong", {"tool": "robot", "tests": ["t.robot"]}, _zip({"t.robot": PASS_ROBOT}))
    assert exc.value.code == 401


def test_http_runs_job(server):
    with _post(server, TOKEN, {"tool": "robot", "tests": ["t.robot"]}, _zip({"t.robot": PASS_ROBOT})) as resp:
        result = json.loads(resp.headers["X-Runner-Result"])
        names = zipfile.ZipFile(io.BytesIO(resp.read())).namelist()
    assert result["returncode"] == 0 and "output.xml" in names
