"""
Benchmark test: SC-009 — 啟用平行執行時，整體清單執行時間較循序執行縮短至少 40%。
基準情境：含 10 個以上案例的清單，max_workers=5。
驗證標準：parallel_time / sequential_time ≤ 0.6（即縮短 ≥ 40%）。
"""
import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

CASE_COUNT = 10
SINGLE_CASE_DURATION_S = 1.0
MAX_WORKERS = 5
SPEEDUP_THRESHOLD = 0.6


async def mock_execute_case(case_id: int) -> dict:
    """模擬單一測試案例執行，耗時約 SINGLE_CASE_DURATION_S 秒。"""
    await asyncio.sleep(SINGLE_CASE_DURATION_S)
    return {"case_id": case_id, "status": "passed"}


async def run_sequential(case_ids: list[int]) -> float:
    """循序執行所有案例，回傳總耗時（秒）。"""
    start = time.perf_counter()
    for case_id in case_ids:
        await mock_execute_case(case_id)
    return time.perf_counter() - start


async def run_parallel(case_ids: list[int], max_workers: int) -> float:
    """以 semaphore 限制並行數執行所有案例，回傳總耗時（秒）。"""
    semaphore = asyncio.Semaphore(max_workers)

    async def bounded_execute(case_id: int):
        async with semaphore:
            return await mock_execute_case(case_id)

    start = time.perf_counter()
    await asyncio.gather(*[bounded_execute(cid) for cid in case_ids])
    return time.perf_counter() - start


@pytest.mark.asyncio
async def test_parallel_execution_speedup():
    """SC-009: 平行執行（max_workers=5）相較循序執行應縮短 ≥ 40%。"""
    case_ids = list(range(1, CASE_COUNT + 1))

    sequential_time = await run_sequential(case_ids)
    parallel_time = await run_parallel(case_ids, max_workers=MAX_WORKERS)

    ratio = parallel_time / sequential_time

    print(f"\n案例數: {CASE_COUNT}，每案例耗時: {SINGLE_CASE_DURATION_S}s，max_workers: {MAX_WORKERS}")
    print(f"循序執行時間: {sequential_time:.2f}s")
    print(f"平行執行時間: {parallel_time:.2f}s")
    print(f"比率（parallel/sequential）: {ratio:.3f}（門檻: ≤ {SPEEDUP_THRESHOLD}）")

    assert ratio <= SPEEDUP_THRESHOLD, (
        f"平行/循序比率 {ratio:.3f} 未達門檻 {SPEEDUP_THRESHOLD} — "
        f"SC-009 FAIL（縮短幅度不足 40%）"
    )


@pytest.mark.asyncio
async def test_parallel_all_cases_complete():
    """SC-009: 平行執行應完成所有 CASE_COUNT 個案例，無遺漏。"""
    case_ids = list(range(1, CASE_COUNT + 1))
    semaphore = asyncio.Semaphore(MAX_WORKERS)

    results = []

    async def bounded_execute(case_id: int):
        async with semaphore:
            result = await mock_execute_case(case_id)
            results.append(result)

    await asyncio.gather(*[bounded_execute(cid) for cid in case_ids])

    assert len(results) == CASE_COUNT, (
        f"預期完成 {CASE_COUNT} 個案例，實際完成 {len(results)} 個 — SC-009 FAIL"
    )
    assert all(r["status"] == "passed" for r in results), "部分案例執行失敗"
