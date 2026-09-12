from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from src.core.config import get_settings
from src.core.dependencies import get_current_user
from src.core.path_utils import safe_join

router = APIRouter(prefix="/media", tags=["media"], dependencies=[Depends(get_current_user)])


def _serve(base: str, *parts: str, not_found_detail: str = "File not found"):
    try:
        file_path = safe_join(base, *parts)
    except ValueError:
        raise HTTPException(status_code=404, detail=not_found_detail)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=not_found_detail)
    return FileResponse(str(file_path))


@router.get("/attachments/{case_id}/{filename}")
async def serve_attachment(case_id: str, filename: str):
    settings = get_settings()
    return _serve(settings.media_root, case_id, filename)


@router.get("/results/{execution_id}/screenshots/{filename}")
async def serve_screenshot(execution_id: str, filename: str):
    settings = get_settings()
    return _serve(
        settings.media_root, "results", execution_id, "screenshots", filename,
        not_found_detail="Screenshot not found",
    )


@router.get("/results/{execution_id}/videos/{filename}")
async def serve_video(execution_id: str, filename: str):
    settings = get_settings()
    resp = _serve(
        settings.media_root, "results", execution_id, "videos", filename,
        not_found_detail="Video not found",
    )
    resp.headers["Accept-Ranges"] = "bytes"
    return resp
