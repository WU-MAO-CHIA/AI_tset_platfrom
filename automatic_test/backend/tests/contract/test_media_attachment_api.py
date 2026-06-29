"""Contract tests for media attachment download endpoint (FR-005 / FR-013 / FR-028).

Validates:
- GET /api/v1/media/attachments/{case_id}/{filename} returns 404 for missing file
- Path traversal attempts are rejected (filename cannot escape media_root)
- Endpoint is registered and reachable
"""

import os
import tempfile
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class TestServeAttachment:
    async def test_missing_file_returns_404(self, client):
        r = await client.get(
            f"/api/v1/media/attachments/{uuid.uuid4()}/nonexistent.png"
        )
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    async def test_existing_file_returns_200(self, client):
        case_id = str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as media_root:
            case_dir = os.path.join(media_root, case_id)
            os.makedirs(case_dir)
            img_path = os.path.join(case_dir, "captcha.png")
            with open(img_path, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

            from src.core.config import get_settings
            settings = get_settings()
            original_root = settings.media_root
            settings.media_root = media_root
            try:
                r = await client.get(f"/api/v1/media/attachments/{case_id}/captcha.png")
                assert r.status_code == 200
            finally:
                settings.media_root = original_root

    async def test_path_traversal_returns_404(self, client):
        # ../../../etc/passwd style attack should result in 404 (file won't exist under media_root)
        r = await client.get(
            "/api/v1/media/attachments/some-case/..%2F..%2Fetc%2Fpasswd"
        )
        assert r.status_code in (404, 422)

    async def test_screenshot_endpoint_missing_returns_404(self, client):
        r = await client.get(
            f"/api/v1/media/results/{uuid.uuid4()}/screenshots/step1.png"
        )
        assert r.status_code == 404

    async def test_video_endpoint_missing_returns_404(self, client):
        r = await client.get(
            f"/api/v1/media/results/{uuid.uuid4()}/videos/session.webm"
        )
        assert r.status_code == 404
