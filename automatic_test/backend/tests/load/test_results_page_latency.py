"""
Load test: SC-013 — 含 50 個媒體項目的執行結果頁面應在 10 秒內載入完成。
驗證標準：GET /api/v1/executions/{id}/results（含 50 個 ExecutionMedia）回應耗時 ≤ 10s。

測試方式：使用 httpx.AsyncClient + ASGITransport 對 FastAPI 應用程式直接測試，
         以 patch.object 覆寫 ExecutionRepository.get，mock AsyncSession.execute
         回傳含 50 個媒體項目的模擬資料，無需啟動外部伺服器。
"""
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.main import app
from src.repositories.execution_repo import ExecutionRepository

MEDIA_COUNT = 50
THRESHOLD_S = 10.0
EXECUTION_ID = "load-test-exec-results-001"
CASE_RESULT_ID = "cr-load-test-001"


def _make_mock_execution_record(execution_id: str):
    record = MagicMock()
    record.id = execution_id
    record.status = "completed"
    record.checklist_id = None
    record.source_case_id = "case-001"
    record.parallel_mode = False
    record.max_workers = 1
    record.passed_count = 1
    record.failed_count = 0
    record.total_count = 1
    return record


def _make_mock_case_result(execution_id: str, cr_id: str):
    cr = MagicMock()
    cr.id = cr_id
    cr.execution_id = execution_id
    cr.test_case_id = "test-case-001"
    cr.status = "passed"
    cr.elapsed_ms = 3200
    cr.failure_message = None
    cr.position = 0
    return cr


def _make_mock_media_items(cr_id: str, count: int) -> list:
    items = []
    for i in range(count):
        m = MagicMock()
        m.id = f"media-{i:03d}"
        m.case_result_id = cr_id
        m.media_type = "screenshot" if i % 3 != 2 else "video"
        m.file_path = f"results/{cr_id}/step{i:03d}.png"
        m.step_index = i
        items.append(m)
    return items


def _build_mock_session(case_result, media_items) -> AsyncMock:
    """建構 AsyncSession mock，根據 SQL 語句回傳對應的模擬資料。"""

    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        scalars_mock = MagicMock()
        result_mock = MagicMock()

        if "execution_media" in stmt_str:
            scalars_mock.all.return_value = media_items
            result_mock.scalar_one_or_none.return_value = None
        elif "case_result" in stmt_str:
            scalars_mock.all.return_value = [case_result]
            result_mock.scalar_one_or_none.return_value = None
        elif "execution_record" in stmt_str:
            scalars_mock.all.return_value = []
            result_mock.scalar_one_or_none.return_value = None
        else:
            scalars_mock.all.return_value = []
            result_mock.scalar_one_or_none.return_value = None

        result_mock.scalars.return_value = scalars_mock
        return result_mock

    session = AsyncMock(spec=AsyncSession)
    session.execute = mock_execute
    return session


@pytest.mark.asyncio
async def test_results_page_with_50_media_within_10s():
    """SC-013: 含 50 個媒體項目的執行結果頁面回應應在 10 秒內完成。"""
    execution_record = _make_mock_execution_record(EXECUTION_ID)
    case_result = _make_mock_case_result(EXECUTION_ID, CASE_RESULT_ID)
    media_items = _make_mock_media_items(CASE_RESULT_ID, MEDIA_COUNT)
    mock_session = _build_mock_session(case_result, media_items)

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    async def mock_repo_get(self, id: str):
        return execution_record if id == EXECUTION_ID else None

    try:
        with patch.object(ExecutionRepository, "get", mock_repo_get):
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                start = time.perf_counter()
                response = await client.get(f"/api/v1/executions/{EXECUTION_ID}/results")
                elapsed = time.perf_counter() - start

        print(
            f"\n結果頁面回應時間: {elapsed * 1000:.1f}ms"
            f"（{MEDIA_COUNT} 個媒體項目；門檻: {THRESHOLD_S}s）"
        )

        assert response.status_code == 200, (
            f"預期 200，實際: {response.status_code}，body: {response.text[:300]}"
        )
        assert elapsed <= THRESHOLD_S, (
            f"結果頁面回應時間 {elapsed:.3f}s 超過門檻 {THRESHOLD_S}s — SC-013 FAIL"
        )

        data = response.json()
        assert "items" in data, "回應應包含 items 欄位"
        assert data["total"] >= 1, "應至少有 1 個案例結果"

        first_item = data["items"][0]
        assert len(first_item["media"]) == MEDIA_COUNT, (
            f"案例結果應包含 {MEDIA_COUNT} 個媒體項目，實際: {len(first_item['media'])}"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_results_page_returns_404_for_unknown_execution():
    """SC-013: 查詢不存在的執行紀錄應回傳 404。"""
    case_result = _make_mock_case_result(EXECUTION_ID, CASE_RESULT_ID)
    media_items = _make_mock_media_items(CASE_RESULT_ID, MEDIA_COUNT)
    mock_session = _build_mock_session(case_result, media_items)

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    async def mock_repo_get(self, id: str):
        return None

    try:
        with patch.object(ExecutionRepository, "get", mock_repo_get):
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                response = await client.get("/api/v1/executions/non-existent-id-xyz/results")

        assert response.status_code == 404, (
            f"未知 execution_id 應回傳 404，實際: {response.status_code}"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)
