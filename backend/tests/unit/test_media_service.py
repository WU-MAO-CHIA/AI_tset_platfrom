"""Unit tests for MediaService.
RED: Tests should fail until MediaService is implemented.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def media_service():
    from src.services.media_service import MediaService
    return MediaService(media_root="/tmp/test_media")


def _make_mock_file(filename: str, content_type: str, data: bytes):
    mock_file = MagicMock()
    mock_file.filename = filename
    mock_file.content_type = content_type
    mock_file.read = AsyncMock(return_value=data)
    mock_file.seek = AsyncMock()
    return mock_file


class TestMediaUploadValidation:
    async def test_validate_image_size_within_limit(self, media_service):
        mock_file = _make_mock_file("test.png", "image/png", b"x" * (5 * 1024 * 1024))
        result = await media_service.validate_file(mock_file)
        assert result["valid"] is True

    async def test_validate_image_exceeds_10mb_limit(self, media_service):
        mock_file = _make_mock_file("big.png", "image/png", b"x" * (11 * 1024 * 1024))
        with pytest.raises(ValueError, match="file_too_large"):
            await media_service.validate_file(mock_file)

    async def test_validate_video_exceeds_100mb_limit(self, media_service):
        mock_file = _make_mock_file("big.mp4", "video/mp4", b"x" * (101 * 1024 * 1024))
        with pytest.raises(ValueError, match="file_too_large"):
            await media_service.validate_file(mock_file)

    async def test_validate_unsupported_file_type(self, media_service):
        mock_file = _make_mock_file("doc.exe", "application/octet-stream", b"data")
        with pytest.raises(ValueError, match="unsupported_file_type"):
            await media_service.validate_file(mock_file)

    def test_generate_path_includes_case_id(self, media_service):
        path = media_service.generate_file_path("case-123", "screenshot.png")
        assert "case-123" in path
        assert "screenshot.png" in path
