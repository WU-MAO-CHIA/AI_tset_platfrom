"""執行佇列 worker（spec 003 第三階段）。

觸發端只寫入 status=pending 的 execution_records；本 worker 在後端啟動時開啟，
依「priority 高者優先、再依 queued_at」領取並執行，同時執行數不超過
EXECUTION_MAX_CONCURRENT。仍是單一 uvicorn 行程，執行本體沿用 ExecutionService。
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

import src.core.database as core_db
from src.execution.events import EventSink
from src.models.execution_event import ExecutionEvent
from src.models.execution_record import ExecutionRecord

logger = logging.getLogger(__name__)

PRIORITY_TRIAL_RUN = 10
PRIORITY_CHECKLIST = 0

_IDLE_POLL_SEC = 5.0
_HEARTBEAT_SEC = 15.0


async def claim_next_pending() -> Optional[ExecutionRecord]:
    """領取下一筆 pending：以條件式 UPDATE 確保同一筆不會被領取兩次。"""
    async with core_db.AsyncSessionLocal() as session:
        result = await session.execute(
            select(ExecutionRecord)
            .where(ExecutionRecord.status == "pending")
            .order_by(ExecutionRecord.priority.desc(), ExecutionRecord.queued_at, ExecutionRecord.created_at)
            .limit(1)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        claimed = await session.execute(
            update(ExecutionRecord)
            .where(ExecutionRecord.id == record.id, ExecutionRecord.status == "pending")
            .values(status="running", started_at=datetime.now(), heartbeat_at=datetime.now())
        )
        await session.commit()
        if claimed.rowcount != 1:
            return None
        await session.refresh(record)
        return record


async def emit_queue_positions(session: Optional[AsyncSession] = None) -> None:
    """替每筆排隊中的執行寫入 execution_queued（前面還有幾筆），讓排隊畫面會前進。

    傳入 session 時在該交易內寫入（由呼叫端 commit），否則自行開啟 session。
    """
    if session is None:
        async with core_db.AsyncSessionLocal() as own_session:
            await emit_queue_positions(own_session)
            await own_session.commit()
        return

    result = await session.execute(
        select(ExecutionRecord.id)
        .where(ExecutionRecord.status == "pending")
        .order_by(ExecutionRecord.priority.desc(), ExecutionRecord.queued_at, ExecutionRecord.created_at)
    )
    for ahead, execution_id in enumerate(result.scalars().all()):
        session.add(ExecutionEvent(
            execution_id=execution_id,
            event="execution_queued",
            payload={
                "event": "execution_queued",
                "execution_id": execution_id,
                "status": "pending",
                "ahead": ahead,
            },
        ))


async def run_execution(record: ExecutionRecord) -> None:
    """依 execution_type 交給既有的執行本體；參數全部來自觸發當下存入的 params。"""
    from src.services.execution_service import ExecutionService

    params = record.params or {}
    if record.execution_type == "trial_run":
        await ExecutionService._execute_trial_bg(
            record.id,
            record.source_case_id,
            rf_code=params.get("rf_code"),
            case_name=params.get("case_name"),
            environment_id=params.get("environment_id"),
        )
    else:
        await ExecutionService._execute_all_cases_bg(
            record.id,
            list(params.get("case_ids") or []),
            int(params.get("concurrency") or 1),
            params.get("environment_overrides") or {},
        )


async def _mark_error(execution_id: str, message: str) -> None:
    async with core_db.AsyncSessionLocal() as session:
        await session.execute(
            update(ExecutionRecord)
            .where(ExecutionRecord.id == execution_id, ExecutionRecord.status == "running")
            .values(status="error", finished_at=datetime.now())
        )
        await session.commit()
    await EventSink(execution_id).emit({
        "event": "execution_error",
        "execution_id": execution_id,
        "message": message,
        "__done__": True,
    })


async def _heartbeat(execution_id: str) -> None:
    while True:
        await asyncio.sleep(_HEARTBEAT_SEC)
        try:
            async with core_db.AsyncSessionLocal() as session:
                await session.execute(
                    update(ExecutionRecord)
                    .where(ExecutionRecord.id == execution_id)
                    .values(heartbeat_at=datetime.now())
                )
                await session.commit()
        except Exception:
            logger.exception("Heartbeat update failed for %s", execution_id)


class ExecutionWorker:
    def __init__(self, max_concurrent: int) -> None:
        self._max_concurrent = max(1, max_concurrent)
        self._slots = asyncio.Semaphore(self._max_concurrent)
        self._wake = asyncio.Event()
        self._loop_task: Optional[asyncio.Task] = None
        self._jobs: set[asyncio.Task] = set()

    @property
    def running(self) -> bool:
        return self._loop_task is not None and not self._loop_task.done()

    def start(self) -> None:
        if not self.running:
            self._loop_task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        tasks = [t for t in [self._loop_task, *self._jobs] if t is not None]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._loop_task = None
        self._jobs.clear()

    def notify(self) -> None:
        """有新的 pending 執行時呼叫，讓 worker 不必等到下一次輪詢。"""
        self._wake.set()

    async def _loop(self) -> None:
        while True:
            await self._slots.acquire()
            # 先清除喚醒旗標再領取，領取之後才到的 notify() 不會被漏掉
            self._wake.clear()
            try:
                record = await claim_next_pending()
            except Exception:
                logger.exception("Claiming next execution failed")
                record = None
            if record is None:
                self._slots.release()
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=_IDLE_POLL_SEC)
                except asyncio.TimeoutError:
                    pass
                continue

            job = asyncio.create_task(self._run(record))
            self._jobs.add(job)
            job.add_done_callback(self._jobs.discard)
            try:
                await emit_queue_positions()
            except Exception:
                logger.exception("Updating queue positions failed")

    async def _run(self, record: ExecutionRecord) -> None:
        heartbeat = asyncio.create_task(_heartbeat(record.id))
        try:
            await run_execution(record)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Execution %s failed in worker", record.id)
            try:
                await _mark_error(record.id, f"執行失敗：{exc}")
            except Exception:
                logger.exception("Marking execution %s as error failed", record.id)
        finally:
            heartbeat.cancel()
            self._slots.release()
            self._wake.set()


_worker: Optional[ExecutionWorker] = None


def get_worker() -> ExecutionWorker:
    global _worker
    if _worker is None:
        from src.core.config import get_settings
        _worker = ExecutionWorker(get_settings().execution_max_concurrent)
    return _worker
