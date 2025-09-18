from fastapi import APIRouter, Query
from database import db

router = APIRouter()

@router.get('/logs')
async def get_logs(limit: int = Query(50, ge=1, le=500)):
    return await db.latest_logs(limit=limit)
