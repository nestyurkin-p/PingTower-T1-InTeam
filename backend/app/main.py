import asyncio
import logging
import sys
from pathlib import Path
from typing import cast

import uvicorn
from fastapi import FastAPI

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import settings  # noqa: E402
from app.broker import app as stream_app  # noqa: E402
import app.consumers  # noqa: F401,E402
from app.api.routes import router as api_router  # noqa: E402
from database import DataBase, db as shared_db  # noqa: E402
if shared_db is None:
    raise RuntimeError("Database connection is not configured")

db = cast(DataBase, shared_db)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="backend-service")
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    await db.create_tables()
    app.state.stream_task = asyncio.create_task(stream_app.run())


@app.on_event("shutdown")
async def shutdown_event():
    task = getattr(app.state, "stream_task", None)
    if task:
        await stream_app.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.backend.host, port=settings.backend.port, reload=False)
