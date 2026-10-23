"""跨 router 共用的回應 schema；各 router 專屬的 schema 定義在各自模組內。"""
from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool


class DeletedResponse(BaseModel):
    deleted: bool


class ExecutionStartResponse(BaseModel):
    execution_id: str
    stream_url: str
