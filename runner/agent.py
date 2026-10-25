"""AutoTest runner：在獨立容器裡執行 Robot Framework / pabot。

後端把一次執行的工作目錄（.robot 腳本 + libs/）打包成 zip POST 到 /run，runner 解開後
以低權限使用者執行，再把整個工作目錄（output.xml、log.html、截圖…）打包回傳。

隔離重點（見 docs/deploy-oracle.md、docker-compose.yml）：
- 容器裡沒有後端的金鑰與資料庫；唯一的秘密是 RUNNER_TOKEN（只能送工作給 runner 自己）。
- agent 以 root 執行，robot 以 RUNNER_RUN_AS（預設 runner）執行：腳本讀不到 agent 的環境變數。
- 指令由 runner 自己組，只接受 robot / pabot 兩種，不接受任意 argv。

只用標準函式庫，image 裡只多 robotframework / Browser / pabot。
"""
from __future__ import annotations

import hmac
import io
import json
import logging
import os
import pwd
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import PurePosixPath

logger = logging.getLogger("runner")

MAX_UPLOAD_BYTES = 50 * 1024 * 1024      # 腳本 + libs
MAX_OUTPUT_BYTES = 300 * 1024 * 1024     # 報告、截圖、影片
MAX_TIMEOUT_SEC = 900
MAX_PROCESSES = 16
TAIL_CHARS = 2000

# 不接受後端覆寫的環境變數（避免改掉 runner 端的執行環境）
_PROTECTED_ENV = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "PWD", "PYTHONPATH", "PYTHONHOME",
                  "PYTHONSTARTUP", "LD_PRELOAD", "LD_LIBRARY_PATH", "PLAYWRIGHT_BROWSERS_PATH",
                  "NODE_OPTIONS", "NODE_PATH", "RUNNER_TOKEN", "RUNNER_RUN_AS"}


class JobError(ValueError):
    """請求內容不合法（回 400）。"""


def _check_rel_path(path: str) -> str:
    p = PurePosixPath(path)
    if not path or p.is_absolute() or ".." in p.parts or "\\" in path or "\x00" in path:
        raise JobError(f"invalid path: {path!r}")
    return str(p)


def build_argv(spec: dict, python: str = sys.executable) -> tuple[list[str], int]:
    """依工作描述組出指令；只接受 robot / pabot 與固定的幾個參數。"""
    tool = spec.get("tool")
    tests = spec.get("tests")
    if tool not in ("robot", "pabot"):
        raise JobError("tool must be robot or pabot")
    if not isinstance(tests, list) or not tests or len(tests) > 500:
        raise JobError("tests must be a non-empty list")
    tests = [_check_rel_path(t) for t in tests]
    od = spec.get("outputdir") or "."
    outputdir = "." if od == "." else _check_rel_path(od)
    try:
        timeout = int(spec.get("timeout", 60))
    except (TypeError, ValueError):
        raise JobError("timeout must be an integer")
    timeout = max(1, min(timeout, MAX_TIMEOUT_SEC))

    if tool == "robot":
        argv = [python, "-m", "robot"]
    else:
        try:
            processes = int(spec.get("processes", 1))
        except (TypeError, ValueError):
            raise JobError("processes must be an integer")
        processes = max(1, min(processes, MAX_PROCESSES))
        # pabot 5.x 沒有 __main__
        argv = [python, "-m", "pabot.pabot", "--processes", str(processes)]
    argv += ["--outputdir", outputdir, "--output", "output.xml", "--nostatusrc", *tests]
    return argv, timeout


def build_env(job_env: dict, home: str) -> dict:
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": home,
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        env["PLAYWRIGHT_BROWSERS_PATH"] = os.environ["PLAYWRIGHT_BROWSERS_PATH"]
    for key, value in (job_env or {}).items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        if key.upper() in _PROTECTED_ENV or key.upper().startswith(("LD_", "PYTHON")):
            continue
        env[key] = value
    return env


def _safe_extract(data: bytes, dest: str) -> None:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise JobError("body must be a zip archive")
    total = 0
    with zf:
        for info in zf.infolist():
            name = _check_rel_path(info.filename.rstrip("/")) if info.filename.rstrip("/") else None
            if name is None:
                continue
            total += info.file_size
            if total > MAX_UPLOAD_BYTES:
                raise JobError("archive too large")
            target = os.path.join(dest, name)
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


def _zip_dir(root: str) -> bytes:
    buf = io.BytesIO()
    total = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _dirs, files in os.walk(root):
            for fname in files:
                full = os.path.join(dirpath, fname)
                if os.path.islink(full):
                    continue  # 不跟隨腳本建立的 symlink（可能指向容器內其他檔案）
                total += os.path.getsize(full)
                if total > MAX_OUTPUT_BYTES:
                    raise RuntimeError("output too large")
                zf.write(full, os.path.relpath(full, root))
    return buf.getvalue()


def _run_as_kwargs(user: str) -> tuple[dict, str]:
    """以 root 執行時降權成 user；非 root（本機開發、測試）就以目前使用者執行。"""
    if not user or os.geteuid() != 0:
        return {}, os.environ.get("HOME", tempfile.gettempdir())
    pw = pwd.getpwnam(user)
    return {"user": pw.pw_uid, "group": pw.pw_gid, "extra_groups": []}, pw.pw_dir


def _tail(f) -> str:
    f.seek(0, os.SEEK_END)
    f.seek(max(0, f.tell() - TAIL_CHARS * 4))
    return f.read().decode("utf-8", "replace")[-TAIL_CHARS:]


def run_job(spec: dict, archive: bytes, run_as: str) -> tuple[dict, bytes]:
    argv, timeout = build_argv(spec)
    drop, home = _run_as_kwargs(run_as)
    env = build_env(spec.get("env") or {}, home)
    workdir = tempfile.mkdtemp(prefix="job-")
    try:
        os.chmod(workdir, 0o777)  # 降權後的使用者要能寫入
        _safe_extract(archive, workdir)
        for dirpath, dirs, _files in os.walk(workdir):
            for d in dirs:
                os.chmod(os.path.join(dirpath, d), 0o777)
        # 輸出寫到暫存檔而不是 pipe：被殺掉時殘留的孫行程（Chromium）不會讓讀取卡住
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            start = time.monotonic()
            proc = subprocess.Popen(
                argv, cwd=workdir, env=env, stdout=out, stderr=err,
                start_new_session=True, umask=0o000, **drop,
            )
            timed_out = False
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
            # 正常結束也清一次：腳本可能留下背景行程
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            proc.wait()
            result = {
                "returncode": proc.returncode,
                "timed_out": timed_out,
                "elapsed_ms": int((time.monotonic() - start) * 1000),
                "stdout_tail": _tail(out),
                "stderr_tail": _tail(err),
            }
        return result, _zip_dir(workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "autotest-runner"
    token: str = ""
    run_as: str = ""

    def log_message(self, fmt, *args):  # noqa: N802 - stdlib 介面
        logger.info("%s " + fmt, self.address_string(), *args)

    def _reply(self, status: int, body: bytes = b"", content_type: str = "application/json",
               result: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if result is not None:
            self.send_header("X-Runner-Result", json.dumps(result))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._reply(status, json.dumps({"error": message}).encode())

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._reply(200, b'{"status":"ok"}')
        else:
            self._error(404, "not found")

    def do_POST(self):  # noqa: N802
        if self.path != "/run":
            return self._error(404, "not found")
        auth = self.headers.get("Authorization", "")
        if not self.token or not hmac.compare_digest(auth.encode(), f"Bearer {self.token}".encode()):
            return self._error(401, "unauthorized")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._error(400, "bad content-length")
        if length <= 0 or length > MAX_UPLOAD_BYTES:
            return self._error(413, "archive too large or empty")
        try:
            spec = json.loads(self.headers.get("X-Runner-Spec", ""))
            if not isinstance(spec, dict):
                raise ValueError
        except ValueError:
            return self._error(400, "X-Runner-Spec must be a JSON object")
        archive = self.rfile.read(length)
        try:
            result, output = run_job(spec, archive, self.run_as)
        except JobError as exc:
            return self._error(400, str(exc))
        except Exception as exc:  # 執行環境問題，回給後端記錄
            logger.exception("job failed")
            return self._error(500, f"runner error: {exc}")
        self._reply(200, output, content_type="application/zip", result=result)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = os.environ.get("RUNNER_TOKEN", "")
    if len(token) < 32:
        raise SystemExit("RUNNER_TOKEN must be set (at least 32 characters)")
    Handler.token = token
    Handler.run_as = os.environ.get("RUNNER_RUN_AS", "runner")
    port = int(os.environ.get("RUNNER_PORT", "9000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    logger.info("runner listening on :%d (robot runs as %s)", port, Handler.run_as)
    server.serve_forever()


if __name__ == "__main__":
    main()
