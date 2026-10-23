"""contract 測試一律在隔離環境執行（見 tests/conftest.py 的 isolated_app）。"""
import pytest


@pytest.fixture(autouse=True)
def _isolated(isolated_app):
    yield
