"""把一次 robot / pabot 執行交給獨立的 runner 容器（EXECUTION_RUNNER=remote）。

工作目錄（腳本、libs/）打包成 zip 送過去，runner 執行完把整個目錄（output.xml、報告、截圖）
打包回傳，解回原本的工作目錄。之後的解析、報告複製與本機執行完全相同。
runner 端見 runner/agent.py。
"""
import asyncio
import io
import json
import os
import time
import zipfile
from pathlib import PurePosixPath

import httpx

from src.core.config import get_settings

MAX_RESULT_BYTES = 300 * 1024 * 1024
# Windows runner 一次只跑一個工作，忙碌時回 409：每隔 BUSY_RETRY_SEC 重送，最多等 BUSY_WAIT_SEC
BUSY_WAIT_SEC = 600
BUSY_RETRY_SEC = 5


class RunnerError(RuntimeError):
    """runner 無法連線或回應錯誤。"""


def _zip_dir(root: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _dirs, files in os.walk(root):
            for fname in files:
                full = os.path.join(dirpath, fname)
                zf.write(full, os.path.relpath(full, root))
    return buf.getvalue()


def _extract(data: bytes, dest: str) -> None:
    """解回工作目錄；runner 執行的是不受信任的腳本，路徑一律檢查不可跳出 dest。"""
    root = os.path.realpath(dest)
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            name = info.filename
            parts = PurePosixPath(name).parts
            if not name or name.startswith("/") or ".." in parts or "\\" in name or info.is_dir():
                continue
            total += info.file_size
            if total > MAX_RESULT_BYTES:
                raise RunnerError("runner output too large")
            target = os.path.realpath(os.path.join(root, *parts))
            if not target.startswith(root + os.sep):
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                while chunk := src.read(1024 * 1024):
                    out.write(chunk)


async def run_remote(workdir: str, spec: dict, env: dict, *, url: str | None = None,
                     token: str | None = None) -> dict:
    """回傳 {"returncode", "timed_out", "stderr_tail", ...}；失敗時 raise RunnerError。

    url / token 未指定時使用 docker compose 內建的 runner（RUNNER_URL / RUNNER_TOKEN）。
    """
    settings = get_settings()
    url = url or settings.runner_url
    token = settings.runner_token if token is None else token
    body = _zip_dir(workdir)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/zip",
        "X-Runner-Spec": json.dumps({**spec, "env": env}),
    }
    # runner 端會在 spec.timeout 秒時結束整組行程，這裡多留時間給打包與傳輸
    timeout = httpx.Timeout(float(spec.get("timeout", 60)) + 120, connect=10)
    deadline = time.monotonic() + BUSY_WAIT_SEC
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            while True:
                resp = await client.post(f"{url.rstrip('/')}/run", content=body, headers=headers)
                if resp.status_code != 409:
                    break
                if time.monotonic() + BUSY_RETRY_SEC > deadline:
                    raise RunnerError(f"測試執行器（runner）持續忙碌超過 {BUSY_WAIT_SEC // 60} 分鐘，請稍後再試")
                await asyncio.sleep(BUSY_RETRY_SEC)
    except httpx.HTTPError as exc:
        raise RunnerError(f"無法連線到測試執行器（runner）：{exc.__class__.__name__}") from exc
    if resp.status_code != 200:
        try:
            detail = resp.json().get("error", "")
        except ValueError:
            detail = resp.text[:200]
        raise RunnerError(f"測試執行器（runner）回應 HTTP {resp.status_code}：{detail}")
    try:
        result = json.loads(resp.headers.get("X-Runner-Result", "{}"))
        _extract(resp.content, workdir)
    except (ValueError, zipfile.BadZipFile) as exc:
        raise RunnerError("測試執行器（runner）回傳的結果格式錯誤") from exc
    return result
