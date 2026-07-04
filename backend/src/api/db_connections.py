from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.dependencies import get_current_user
from src.models.db_connection import DBConnection
from src.services.db_connect_service import DBConnectionService

router = APIRouter(prefix="/db-connections", tags=["db-connections"], dependencies=[Depends(get_current_user)])


class DBConnectionCreateRequest(BaseModel):
    name: str
    connection_string: str
    created_by: str
    description: Optional[str] = None


class QueryRequest(BaseModel):
    sql: str


class DBConnectionResponse(BaseModel):
    id: str
    name: str
    created_by: str
    description: Optional[str] = None
    last_test_success: Optional[bool] = None


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DBConnectionResponse)
async def create_connection(body: DBConnectionCreateRequest, db: AsyncSession = Depends(get_db)):
    conn = DBConnection(
        name=body.name,
        connection_string=body.connection_string,
        created_by=body.created_by,
        description=body.description,
    )
    db.add(conn)
    await db.flush()
    await db.refresh(conn)
    return DBConnectionResponse(
        id=conn.id, name=conn.name, created_by=conn.created_by, description=conn.description
    )


@router.get("", response_model=dict)
async def list_connections(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DBConnection))
    items = result.scalars().all()
    return {
        "items": [
            {"id": c.id, "name": c.name, "created_by": c.created_by, "last_test_success": c.last_test_success}
            for c in items
        ]
    }


@router.post("/{conn_id}/test")
async def test_connection(conn_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DBConnection).where(DBConnection.id == conn_id))
    conn = result.scalar_one_or_none()
    if conn is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    service = DBConnectionService()
    test_result = await service.test_connection(conn.connection_string)

    from sqlalchemy.sql import func
    conn.last_tested_at = func.now()
    conn.last_test_success = test_result["success"]
    await db.flush()

    return test_result


@router.post("/{conn_id}/query")
async def execute_query(conn_id: str, body: QueryRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DBConnection).where(DBConnection.id == conn_id))
    conn = result.scalar_one_or_none()
    if conn is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    service = DBConnectionService()
    try:
        query_result = await service.execute_query(conn.connection_string, body.sql)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "query_error", "message": str(exc)})
    return query_result
