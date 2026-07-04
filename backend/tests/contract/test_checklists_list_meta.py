"""Contract test：/checklists 列表須回傳 case_count / status / created_at。

修復「/checklists 案例數與狀態未顯示」——列表端點先前只回 id/name/created_by/description。
"""
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _admin_token(client) -> str:
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert r.status_code == 200
    return r.json()["access_token"]


class TestChecklistListMeta:
    async def test_list_items_include_case_count_status_created_at(self, client):
        token = await _admin_token(client)
        r = await client.get("/api/v1/checklists?page=1&page_size=5", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        for item in data["items"]:
            assert "case_count" in item
            assert isinstance(item["case_count"], int)
            assert "status" in item          # 未執行為 None
            assert "created_at" in item

    @pytest.mark.parametrize("order", ["asc", "desc"])
    async def test_sort_by_status_custom_priority(self, client, order):
        # 自訂優先序：completed → pending → running → failed → error → 未執行
        rank = {"completed": 0, "pending": 1, "running": 2, "failed": 3, "error": 4}
        token = await _admin_token(client)
        r = await client.get(
            f"/api/v1/checklists?page=1&page_size=20&sort_by=status&order={order}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        ranks = [rank.get(item["status"], 99) for item in r.json()["items"]]
        # asc：rank 由小到大（completed 在前）；desc：反之
        assert ranks == sorted(ranks, reverse=(order == "desc"))
