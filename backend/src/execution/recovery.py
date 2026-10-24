"""後端啟動時的執行狀態恢復（spec 003 第一階段）。

執行在行程內以 asyncio task 進行，行程重啟後不會有人接手；
啟動時把殘留的 running 記錄標為 interrupted，避免畫面永遠顯示執行中。
"""

import logging
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.execution_event import ExecutionEvent
from src.models.execution_record import ExecutionRecord

logger = logging.getLogger(__name__)

# 不會再變動的狀態；SSE 與前端以此判斷執行已結束
TERMINAL_STATUSES = ("completed", "failed", "error", "interrupted", "cancelled")


async def mark_interrupted_executions(session: AsyncSession) -> int:
    """running → interrupted，並為每筆寫一筆 execution_interrupted 事件。回傳處理筆數。"""
    result = await session.execute(
        select(ExecutionRecord.id).where(ExecutionRecord.status == "running")
    )
    ids = list(result.scalars().all())
    if not ids:
        return 0

    await session.execute(
        update(ExecutionRecord)
        .where(ExecutionRecord.id.in_(ids), ExecutionRecord.status == "running")
        .values(status="interrupted", finished_at=datetime.now())
    )
    for execution_id in ids:
        session.add(ExecutionEvent(
            execution_id=execution_id,
            event="execution_interrupted",
            payload={
                "event": "execution_interrupted",
                "execution_id": execution_id,
                "status": "interrupted",
                "message": "執行因服務重啟而中斷",
                "__done__": True,
            },
        ))
    await session.commit()
    logger.warning("Marked %d running execution(s) as interrupted after restart", len(ids))
    return len(ids)
