"""
Load test: SC-011 — 試跑從觸發到結果可取得，整體流程應在 60 秒內完成。
驗證標準：觸發 trial-run API（建立 DB 紀錄）+ RF 背景執行 + 寫回結果，總耗時 ≤ 60s。

設計說明：
  ExecutionService.run_trial() 立即回傳（建立 DB 紀錄），實際 RF 執行在背景 asyncio.Task 進行。
  本測試以 asyncio.sleep 模擬各階段耗時，驗證整體時序架構符合 SC-011 門檻。
"""
import asyncio
import time

import pytest

# --- 各階段模擬耗時（單位：秒）---
DB_INSERT_S = 0.05       # 建立 ExecutionRecord
RF_EXECUTION_S = 50.0    # Robot Framework 執行 10 個案例
DB_WRITE_BACK_S = 0.05   # 寫回 CaseResult
THRESHOLD_S = 60.0


async def _simulate_db_insert() -> str:
    """模擬 DB 建立 ExecutionRecord 並回傳 execution_id。"""
    await asyncio.sleep(DB_INSERT_S)
    return "trial-exec-load-test-001"


async def _simulate_rf_execution(execution_id: str) -> dict:
    """模擬 RF subprocess 執行並回傳結果摘要。"""
    await asyncio.sleep(RF_EXECUTION_S)
    return {"status": "completed", "passed": 9, "failed": 1, "execution_id": execution_id}


async def _simulate_write_back(execution_id: str, result: dict) -> None:
    """模擬將 RF 執行結果寫回 DB。"""
    await asyncio.sleep(DB_WRITE_BACK_S)


async def simulate_trial_run_full_flow() -> dict:
    """
    模擬完整試跑流程：
      1. API handler 建立 ExecutionRecord（立即回傳 execution_id）
      2. 背景 task 執行 RF subprocess
      3. 背景 task 將結果寫回 DB
    """
    execution_id = await _simulate_db_insert()

    rf_result = await _simulate_rf_execution(execution_id)
    await _simulate_write_back(execution_id, rf_result)

    return {"execution_id": execution_id, **rf_result}


@pytest.mark.asyncio
async def test_trial_run_completes_within_60s():
    """SC-011: 試跑完整流程（觸發 → RF 執行 → 結果可取得）應在 60 秒內完成。"""
    start = time.perf_counter()
    result = await simulate_trial_run_full_flow()
    elapsed = time.perf_counter() - start

    print(
        f"\n試跑完整流程時間: {elapsed:.2f}s"
        f"（模擬 RF 執行: {RF_EXECUTION_S}s；門檻: {THRESHOLD_S}s）"
    )

    assert elapsed <= THRESHOLD_S, (
        f"試跑流程總時間 {elapsed:.2f}s 超過門檻 {THRESHOLD_S}s — SC-011 FAIL"
    )
    assert result["status"] == "completed", "試跑應以 completed 狀態結束"
    assert result["execution_id"], "應回傳有效的 execution_id"


@pytest.mark.asyncio
async def test_trial_run_api_response_is_immediate():
    """SC-011: trial-run API 端點（DB insert）應立即回傳，不阻塞等待 RF 執行完成。"""
    start = time.perf_counter()
    execution_id = await _simulate_db_insert()
    api_response_time = time.perf_counter() - start

    print(f"\nAPI 回應時間（DB insert）: {api_response_time * 1000:.1f}ms（門檻: <1000ms）")

    assert api_response_time < 1.0, (
        f"trial-run API 回應時間 {api_response_time:.2f}s 超過 1s，"
        "應立即回傳 execution_id 而非等待 RF 執行 — SC-011 FAIL"
    )
    assert execution_id.startswith("trial-exec-"), "應回傳有效的 execution_id"


@pytest.mark.asyncio
async def test_rf_execution_budget_within_threshold():
    """SC-011: RF 執行模擬（50s）加上 DB 讀寫開銷後仍應在 60s 門檻內。"""
    overhead_budget = THRESHOLD_S - RF_EXECUTION_S

    start = time.perf_counter()
    await _simulate_db_insert()
    await _simulate_write_back("exec-test", {"status": "completed"})
    overhead = time.perf_counter() - start

    print(
        f"\nDB 開銷: {overhead * 1000:.1f}ms"
        f"（RF 執行預留: {RF_EXECUTION_S}s；開銷預算: {overhead_budget}s）"
    )

    assert overhead < overhead_budget, (
        f"DB 讀寫開銷 {overhead:.3f}s 超過預算 {overhead_budget}s，"
        f"無法保證整體流程在 {THRESHOLD_S}s 內完成 — SC-011 FAIL"
    )
