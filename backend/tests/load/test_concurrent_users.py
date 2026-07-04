"""
Load test: SC-006 — 平台支援至少 10 位測試人員同時操作而不出現效能衰退。
驗證標準：10 個並發 GET /cases 請求的 p95 回應時間 ≤ 2000ms。
"""
import asyncio
import statistics
import time

import httpx
import pytest

BASE_URL = "http://localhost:8000"
CONCURRENT_USERS = 10
P95_THRESHOLD_MS = 2000


async def _login(client: httpx.AsyncClient) -> dict[str, str]:
    """登入取得 JWT，回傳 Authorization header。"""
    resp = await client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert resp.status_code == 200, f"登入失敗: {resp.status_code} {resp.text[:200]}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def fetch_cases(client: httpx.AsyncClient, headers: dict[str, str]) -> float:
    start = time.perf_counter()
    response = await client.get(f"{BASE_URL}/api/v1/cases", headers=headers)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert response.status_code == 200, f"Unexpected status: {response.status_code}"
    return elapsed_ms


@pytest.mark.asyncio
async def test_concurrent_users_p95_response_time():
    """SC-006: 10 位並發使用者的 p95 回應時間應 ≤ 2000ms。"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = await _login(client)
        tasks = [fetch_cases(client, headers) for _ in range(CONCURRENT_USERS)]
        response_times = await asyncio.gather(*tasks)

    sorted_times = sorted(response_times)
    p95_index = int(len(sorted_times) * 0.95) - 1
    p95_ms = sorted_times[max(p95_index, 0)]
    avg_ms = statistics.mean(response_times)

    print(f"\n並發使用者數: {CONCURRENT_USERS}")
    print(f"平均回應時間: {avg_ms:.1f}ms")
    print(f"p95 回應時間: {p95_ms:.1f}ms（門檻: {P95_THRESHOLD_MS}ms）")
    print(f"所有回應時間: {[f'{t:.1f}' for t in sorted_times]}")

    assert p95_ms <= P95_THRESHOLD_MS, (
        f"p95 回應時間 {p95_ms:.1f}ms 超過門檻 {P95_THRESHOLD_MS}ms — SC-006 FAIL"
    )


@pytest.mark.asyncio
async def test_all_concurrent_requests_succeed():
    """SC-006: 10 個並發請求均應返回 200，無請求失敗。"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = await _login(client)
        tasks = [fetch_cases(client, headers) for _ in range(CONCURRENT_USERS)]
        response_times = await asyncio.gather(*tasks, return_exceptions=True)

    failures = [r for r in response_times if isinstance(r, Exception)]
    assert len(failures) == 0, (
        f"{len(failures)} 個請求失敗 — SC-006 FAIL\n失敗詳情: {failures}"
    )
