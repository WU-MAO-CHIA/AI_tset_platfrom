"""執行環境（spec 005）：admin 登記的 runner，以及 docker compose 內建的「預設容器」。

內建環境不存在 DB，以固定 id（BUILTIN_ENVIRONMENT_ID）代表，位址與 token 來自
RUNNER_URL / RUNNER_TOKEN；EXECUTION_RUNNER=local 時代表後端自己執行。
連線狀態只存在記憶體（單一後端行程），由背景每 60 秒檢查一次。
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.secret_box import SecretDecryptError, decrypt_secret, encrypt_secret
from src.models.runner_environment import (
    BUILTIN_ENVIRONMENT_ID,
    ENVIRONMENT_KINDS,
    KIND_LINUX,
    RunnerEnvironment,
)

logger = logging.getLogger(__name__)

BUILTIN_ENVIRONMENT_NAME = "預設容器"

# 連線狀態
STATUS_ONLINE = "online"
STATUS_BUSY = "busy"
STATUS_OFFLINE = "offline"
STATUS_UNAUTHORIZED = "unauthorized"
STATUS_LOCAL = "local"  # EXECUTION_RUNNER=local：後端自己執行
STATUS_UNKNOWN = "unknown"

_HEALTH_TIMEOUT_SEC = 5.0
_health: dict[str, dict] = {}


class EnvironmentUnavailable(ValueError):
    """指定的執行環境不存在、已停用或無法使用。"""


@dataclass(frozen=True)
class RunnerTarget:
    """一次執行要送往的 runner。url 為 None 表示內建環境（依 EXECUTION_RUNNER 決定本機或容器）。"""

    id: str
    name: str
    kind: str
    url: Optional[str] = None
    token: Optional[str] = None


BUILTIN_TARGET = RunnerTarget(id=BUILTIN_ENVIRONMENT_ID, name=BUILTIN_ENVIRONMENT_NAME, kind=KIND_LINUX)


def get_health(environment_id: str) -> dict:
    return _health.get(environment_id, {"status": STATUS_UNKNOWN, "checked_at": None})


def mark_unauthorized(environment_id: str) -> None:
    """token 無法解密時的狀態（不必連線就知道無法使用）。"""
    _health[environment_id] = {"status": STATUS_UNAUTHORIZED, "checked_at": datetime.now(timezone.utc).isoformat()}


def reset_health_cache() -> None:
    _health.clear()


def _validate_url(url: str) -> str:
    url = (url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("位址必須是 http:// 或 https:// 開頭的網址")
    return url.rstrip("/")


def _validate_kind(kind: str) -> str:
    if kind not in ENVIRONMENT_KINDS:
        raise ValueError(f"類型必須是 {' / '.join(ENVIRONMENT_KINDS)}")
    return kind


def _validate_name(name: str) -> str:
    name = (name or "").strip()
    if not name or len(name) > 100:
        raise ValueError("名稱必須是 1 到 100 個字")
    if name == BUILTIN_ENVIRONMENT_NAME:
        raise ValueError("名稱與內建環境重複")
    return name


async def check_health(target: RunnerTarget) -> dict:
    """呼叫 runner 的 /health 並更新快取。"""
    now = datetime.now(timezone.utc).isoformat()
    if target.url is None and get_settings().execution_runner != "remote":
        result = {"status": STATUS_LOCAL, "checked_at": now}
        _health[target.id] = result
        return result

    url = target.url or get_settings().runner_url
    token = target.token if target.url else get_settings().runner_token
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT_SEC) as client:
            resp = await client.get(f"{url.rstrip('/')}/health", headers=headers)
        body = resp.json() if resp.status_code == 200 else {}
    except (httpx.HTTPError, ValueError):
        body = None
    if not body or body.get("status") != "ok":
        status = STATUS_OFFLINE
    elif body.get("authorized") is False or not token:
        status = STATUS_UNAUTHORIZED
    elif body.get("active_jobs"):
        status = STATUS_BUSY
    else:
        status = STATUS_ONLINE
    result = {"status": status, "checked_at": now}
    _health[target.id] = result
    return result


class RunnerEnvironmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_rows(self) -> list[RunnerEnvironment]:
        result = await self._session.execute(select(RunnerEnvironment).order_by(RunnerEnvironment.name))
        return list(result.scalars().all())

    async def get_row(self, environment_id: str) -> Optional[RunnerEnvironment]:
        if environment_id == BUILTIN_ENVIRONMENT_ID:
            return None
        return await self._session.get(RunnerEnvironment, environment_id)

    async def create(self, *, name: str, kind: str, url: str, token: str, enabled: bool = True) -> RunnerEnvironment:
        if not token:
            raise ValueError("請輸入 token")
        row = RunnerEnvironment(
            name=_validate_name(name),
            kind=_validate_kind(kind),
            url=_validate_url(url),
            token_encrypted=encrypt_secret(token),
            enabled=enabled,
        )
        self._session.add(row)
        await self._flush_unique()
        return row

    async def update(self, environment_id: str, **fields) -> Optional[RunnerEnvironment]:
        """只更新有帶的欄位；token 為空表示不變。類型建立後不能修改（案例依類型決定網頁或桌面）。"""
        if environment_id == BUILTIN_ENVIRONMENT_ID:
            raise ValueError("內建環境不能修改")
        row = await self.get_row(environment_id)
        if row is None:
            return None
        if fields.get("name") is not None:
            row.name = _validate_name(fields["name"])
        if fields.get("url") is not None:
            row.url = _validate_url(fields["url"])
        if fields.get("token"):
            row.token_encrypted = encrypt_secret(fields["token"])
        if fields.get("enabled") is not None:
            row.enabled = fields["enabled"]
        await self._flush_unique()
        _health.pop(environment_id, None)
        return row

    async def delete(self, environment_id: str) -> bool:
        """刪除環境；引用它的 linux 案例改回內建環境，windows 案例需重新選擇（設為 null）。"""
        from src.models.execution_schedule import ExecutionSchedule
        from src.models.test_case import TestCase

        if environment_id == BUILTIN_ENVIRONMENT_ID:
            raise ValueError("內建環境不能刪除")
        row = await self.get_row(environment_id)
        if row is None:
            return False
        fallback = BUILTIN_ENVIRONMENT_ID if row.kind == KIND_LINUX else None
        await self._session.execute(
            update(TestCase).where(TestCase.runner_environment_id == environment_id)
            .values(runner_environment_id=fallback)
        )
        for column in (ExecutionSchedule.linux_environment_id, ExecutionSchedule.windows_environment_id):
            await self._session.execute(
                update(ExecutionSchedule).where(column == environment_id).values({column.key: None})
            )
        await self._session.delete(row)
        await self._session.flush()
        _health.pop(environment_id, None)
        return True

    async def kinds(self, environment_ids: set[str]) -> dict[str, str]:
        """環境 id → 類型（內建環境為 linux）；不存在的 id 不會出現在結果中。"""
        kinds = {BUILTIN_ENVIRONMENT_ID: KIND_LINUX} if BUILTIN_ENVIRONMENT_ID in environment_ids else {}
        others = environment_ids - {BUILTIN_ENVIRONMENT_ID}
        if others:
            result = await self._session.execute(
                select(RunnerEnvironment.id, RunnerEnvironment.kind).where(RunnerEnvironment.id.in_(others))
            )
            kinds.update(dict(result.all()))
        return kinds

    async def require_selectable(self, environment_id: str) -> str:
        """案例要設定的預設環境必須存在且啟用；回傳其類型。"""
        if environment_id == BUILTIN_ENVIRONMENT_ID:
            return KIND_LINUX
        row = await self.get_row(environment_id)
        if row is None or not row.enabled:
            raise ValueError("執行環境不存在或已停用")
        return row.kind

    async def kind_of(self, environment_id: Optional[str]) -> Optional[str]:
        if not environment_id:
            return None
        return (await self.kinds({environment_id})).get(environment_id)

    async def require_kind(self, environment_id: Optional[str], kind: str) -> None:
        """執行時改選的環境必須存在、啟用且類型相符。"""
        if not environment_id:
            return
        if environment_id == BUILTIN_ENVIRONMENT_ID:
            if kind != KIND_LINUX:
                raise ValueError("內建環境只能執行網頁測試")
            return
        row = await self.get_row(environment_id)
        if row is None or not row.enabled:
            raise ValueError("執行環境不存在或已停用")
        if row.kind != kind:
            raise ValueError("執行環境的類型不符")

    async def resolve(self, environment_id: Optional[str]) -> RunnerTarget:
        if environment_id == BUILTIN_ENVIRONMENT_ID:
            return BUILTIN_TARGET
        if not environment_id:
            raise EnvironmentUnavailable("案例的執行環境已被刪除，請重新選擇")
        row = await self.get_row(environment_id)
        if row is None:
            raise EnvironmentUnavailable("執行環境不存在，請重新選擇")
        if not row.enabled:
            raise EnvironmentUnavailable(f"執行環境「{row.name}」已停用")
        return self.to_target(row)

    @staticmethod
    def to_target(row: RunnerEnvironment) -> RunnerTarget:
        try:
            token = decrypt_secret(row.token_encrypted) if row.token_encrypted else ""
        except SecretDecryptError as exc:
            raise EnvironmentUnavailable(f"執行環境「{row.name}」的 token 無法解密，請重新輸入") from exc
        return RunnerTarget(id=row.id, name=row.name, kind=row.kind, url=row.url, token=token)

    async def _flush_unique(self) -> None:
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ValueError("名稱已被使用") from exc


async def check_all_environments() -> None:
    """背景健康檢查：內建環境與所有啟用中的環境。"""
    import src.core.database as core_db

    targets = [BUILTIN_TARGET]
    async with core_db.AsyncSessionLocal() as session:
        for row in await RunnerEnvironmentService(session).list_rows():
            if not row.enabled:
                continue
            try:
                targets.append(RunnerEnvironmentService.to_target(row))
            except EnvironmentUnavailable:
                mark_unauthorized(row.id)
    await asyncio.gather(*(check_health(t) for t in targets), return_exceptions=True)


class RunnerHealthMonitor:
    """與 ScheduleRunner 相同：在 startup 開啟的 asyncio task。"""

    _INTERVAL_SEC = 60.0

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def _loop(self) -> None:
        while True:
            try:
                await check_all_environments()
            except Exception:
                logger.exception("Runner health check failed")
            await asyncio.sleep(self._INTERVAL_SEC)


_monitor: Optional[RunnerHealthMonitor] = None


def get_health_monitor() -> RunnerHealthMonitor:
    global _monitor
    if _monitor is None:
        _monitor = RunnerHealthMonitor()
    return _monitor
