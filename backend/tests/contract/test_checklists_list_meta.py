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


class TestChecklistRecentRuns:
    async def test_recent_runs_are_newest_first_and_capped(self, isolated_app, admin_headers):
        from datetime import datetime, timedelta, timezone

        from src.models.execution_record import ExecutionRecord

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=admin_headers) as c:
            r = await c.post("/api/v1/checklists", json={"name": "冒煙測試", "created_by": "admin"})
            checklist_id = r.json()["id"]
            empty_id = (await c.post("/api/v1/checklists", json={"name": "未執行", "created_by": "admin"})).json()["id"]

            base = datetime(2026, 10, 1, tzinfo=timezone.utc)
            async with isolated_app() as session:
                for i in range(12):
                    session.add(
                        ExecutionRecord(
                            id=f"run-{i:02d}",
                            checklist_id=checklist_id,
                            status="completed",
                            passed_count=3,
                            failed_count=1 if i % 4 == 0 else 0,
                            total_count=3,
                            created_at=base + timedelta(hours=i),
                        )
                    )
                session.add(
                    ExecutionRecord(
                        id="run-deleted", checklist_id=checklist_id, status="deleted", created_at=base + timedelta(days=1)
                    )
                )
                await session.commit()

            items = {i["id"]: i for i in (await c.get("/api/v1/checklists?page=1&page_size=20")).json()["items"]}

        runs = items[checklist_id]["recent_runs"]
        assert [run["id"] for run in runs] == [f"run-{i:02d}" for i in range(11, 1, -1)]
        assert runs[0]["failed_count"] == 0 and runs[3]["failed_count"] == 1
        assert items[checklist_id]["status"] == "completed"
        assert items[empty_id]["recent_runs"] == []
