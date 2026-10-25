"""頁面探索：每個請求（含重導向、頁內 fetch）都重新檢查主機，擋住內網與雲端 metadata。"""
from src.services.page_explorer_service import PageExplorerService


class FakeRoute:
    def __init__(self, url: str):
        self.request = type("Req", (), {"url": url})()
        self.result = None

    async def continue_(self):
        self.result = "continue"

    async def abort(self, reason: str = "failed"):
        self.result = f"abort:{reason}"


async def _guard(url: str) -> str:
    route = FakeRoute(url)
    await PageExplorerService()._guard_request(route)
    return route.result


async def test_metadata_endpoint_blocked():
    assert await _guard("http://169.254.169.254/opc/v2/instance/") == "abort:blockedbyclient"


async def test_loopback_and_private_blocked():
    assert (await _guard("http://127.0.0.1:8000/api/v1/admin/users")).startswith("abort")
    assert (await _guard("http://10.0.0.5/")).startswith("abort")


async def test_file_scheme_blocked():
    assert (await _guard("file:///etc/passwd")).startswith("abort")


async def test_data_url_allowed():
    assert await _guard("data:text/plain,hello") == "continue"


async def test_public_ip_allowed():
    assert await _guard("https://1.1.1.1/") == "continue"
