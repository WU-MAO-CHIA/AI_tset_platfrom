"""
Load test: SC-007 — AI 補齊測試步驟應在 15 秒內完成（含 LLM 呼叫延遲）。
驗證標準：complete_steps() 在模擬 LLM 延遲 12s 的情境下，總耗時 ≤ 15s。
"""
import asyncio
import time

import pytest

from src.services.ai_service import AIService

LLM_SIMULATED_DELAY_S = 12.0
THRESHOLD_S = 15.0


class MockLLMProvider:
    """模擬 LLM Provider：complete() 延遲 LLM_SIMULATED_DELAY_S 秒後回傳補齊步驟。"""

    async def complete(self, prompt: str) -> str:
        await asyncio.sleep(LLM_SIMULATED_DELAY_S)
        return (
            "1. 開啟登入頁面\n"
            "2. 在帳號欄位輸入有效使用者名稱\n"
            "3. 在密碼欄位輸入正確密碼\n"
            "4. 點擊「登入」按鈕\n"
            "5. 驗證頁面跳轉至首頁\n"
            "6. 確認頂部顯示使用者名稱"
        )

    async def complete_with_vision(self, prompt: str, media: list) -> str:
        return await self.complete(prompt)

    async def complete_with_messages(self, messages: list, system: str = "") -> str:
        return await self.complete(system)


@pytest.mark.asyncio
async def test_ai_complete_steps_within_15s():
    """SC-007: AI 補齊步驟（含 12s LLM 延遲）應在 15 秒內完成。"""
    service = AIService(provider=MockLLMProvider())

    start = time.perf_counter()
    result = await service.complete_steps(
        partial_steps="1. 開啟登入頁面",
        description="驗證使用者登入功能正常運作",
    )
    elapsed = time.perf_counter() - start

    print(
        f"\nAI 補齊時間: {elapsed:.2f}s"
        f"（模擬 LLM 延遲: {LLM_SIMULATED_DELAY_S}s；門檻: {THRESHOLD_S}s）"
    )

    assert elapsed <= THRESHOLD_S, (
        f"AI 補齊時間 {elapsed:.2f}s 超過門檻 {THRESHOLD_S}s — SC-007 FAIL"
    )
    assert result.strip(), "AI 補齊結果不應為空"
    assert "登入" in result, "AI 補齊結果應包含測試步驟內容"


@pytest.mark.asyncio
async def test_ai_complete_steps_overhead_under_3s():
    """SC-007: AIService 自身開銷（不含 LLM 延遲）應 < 3s。"""
    FAST_DELAY = 0.05

    class FastMockProvider:
        async def complete(self, prompt: str) -> str:
            await asyncio.sleep(FAST_DELAY)
            return "1. 步驟一\n2. 步驟二\n3. 步驟三"

        async def complete_with_vision(self, prompt: str, media: list) -> str:
            return await self.complete(prompt)

    service = AIService(provider=FastMockProvider())

    start = time.perf_counter()
    result = await service.complete_steps(
        partial_steps="1. 點擊按鈕",
        description="測試功能",
    )
    elapsed = time.perf_counter() - start

    overhead = elapsed - FAST_DELAY
    print(f"\nAIService 開銷: {overhead * 1000:.1f}ms（門檻: <3000ms）")

    assert overhead < 3.0, (
        f"AIService 開銷 {overhead:.2f}s 超過 3s，prompt 建構或其他處理過慢"
    )
    assert result.strip(), "結果不應為空"
