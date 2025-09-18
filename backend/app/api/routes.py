from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session
from app.db import crud
from app.schemas import LogEntryOut

router = APIRouter()


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


@router.get("/logs", response_model=List[LogEntryOut])
async def get_logs(limit: int = Query(50, ge=1, le=500), session: AsyncSession = Depends(get_session)):
    items = await crud.list_logs(session, limit=limit)
    return items
