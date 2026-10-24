"""執行進度事件的寫入與讀取（spec 003 第二階段）。

事件寫入 execution_events，SSE 端點從 DB 讀取推送；
重新整理頁面或後端重啟後，進度可以從 DB 補齊。
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import src.core.database as core_db
from src.models.execution_event import ExecutionEvent

logger = logging.getLogger(__name__)


class EventSink:
    """取代原本的記憶體 asyncio.Queue：emit() 的 payload 格式不變，改為寫入 DB。"""

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id

    async def emit(self, payload: dict) -> None:
        try:
            async with core_db.AsyncSessionLocal() as session:
                session.add(ExecutionEvent(
                    execution_id=self.execution_id,
                    event=str(payload.get("event", "")),
                    payload=payload,
                ))
                await session.commit()
        except Exception:
            # 進度事件寫入失敗不應中斷測試執行；最終狀態仍由 execution_records 決定
            logger.exception("Failed to write execution event for %s", self.execution_id)


async def fetch_events_after(
    session: AsyncSession, execution_id: str, after_id: int, limit: int = 500
) -> list[ExecutionEvent]:
    result = await session.execute(
        select(ExecutionEvent)
        .where(ExecutionEvent.execution_id == execution_id, ExecutionEvent.id > after_id)
        .order_by(ExecutionEvent.id)
        .limit(limit)
    )
    return list(result.scalars().all())
