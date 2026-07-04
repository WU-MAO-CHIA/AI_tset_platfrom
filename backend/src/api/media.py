import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.core.config import get_settings

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/attachments/{case_id}/{filename}")
async def serve_attachment(case_id: str, filename: str):
    settings = get_settings()
    file_path = os.path.join(settings.media_root, case_id, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@router.get("/results/{execution_id}/screenshots/{filename}")
async def serve_screenshot(execution_id: str, filename: str):
    settings = get_settings()
    file_path = os.path.join(settings.media_root, "results", execution_id, "screenshots", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(file_path)


@router.get("/results/{execution_id}/videos/{filename}")
async def serve_video(execution_id: str, filename: str):
    settings = get_settings()
    file_path = os.path.join(settings.media_root, "results", execution_id, "videos", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(file_path, headers={"Accept-Ranges": "bytes"})
