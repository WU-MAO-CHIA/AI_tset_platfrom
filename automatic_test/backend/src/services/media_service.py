import os
import uuid
from pathlib import Path
from typing import Optional

import aiofiles

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
IMAGE_MAX_BYTES = 10 * 1024 * 1024   # 10 MB
VIDEO_MAX_BYTES = 100 * 1024 * 1024  # 100 MB


class MediaService:
    def __init__(self, media_root: str) -> None:
        self.media_root = Path(media_root)

    def generate_file_path(self, case_id: str, filename: str) -> str:
        safe_name = Path(filename).name
        dest_dir = self.media_root / "attachments" / case_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"{uuid.uuid4()}_{safe_name}"
        return str(dest_dir / unique_name)

    async def validate_file(self, file) -> dict:
        content_type = getattr(file, "content_type", "") or ""
        filename = getattr(file, "filename", "") or ""
        data = await file.read()
        size = len(data)

        if content_type in ALLOWED_IMAGE_TYPES:
            if size > IMAGE_MAX_BYTES:
                raise ValueError("file_too_large")
        elif content_type in ALLOWED_VIDEO_TYPES:
            if size > VIDEO_MAX_BYTES:
                raise ValueError("file_too_large")
        else:
            raise ValueError("unsupported_file_type")

        await file.seek(0)
        return {"valid": True, "size": size, "content_type": content_type}

    async def save_file(self, case_id: str, filename: str, data: bytes) -> str:
        file_path = self.generate_file_path(case_id, filename)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data)
        return file_path

    async def upload_attachment(self, case_id: str, file, url: Optional[str] = None):
        if url:
            return {
                "attachment_type": "url",
                "url": url,
                "filename": None,
                "file_path": None,
                "file_size_bytes": None,
                "mime_type": None,
            }

        await self.validate_file(file)
        data = await file.read()
        file_path = await self.save_file(case_id, file.filename, data)
        content_type = file.content_type or ""
        attachment_type = "video" if content_type.startswith("video/") else "image"

        return {
            "attachment_type": attachment_type,
            "filename": file.filename,
            "file_path": file_path,
            "url": None,
            "file_size_bytes": len(data),
            "mime_type": content_type,
        }

    async def delete_attachment(self, file_path: str) -> bool:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        return False
