import asyncio
import logging
import uvicorn
from fastapi import FastAPI
from app.broker import app as stream_app
from app.consumers import pinger as _p1  # noqa: F401
from app.consumers import llm as _p2  # noqa: F401
from app.db.session import init_models
from app.config import app_cfg
from app.api.routes import router as api_router

logger = logging.getLogger(__name__)
logging.basicConfig(level=getattr(logging, app_cfg.log_level.upper(), logging.INFO),
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(title="backend-service")
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    await init_models()
    app.state.stream_task = asyncio.create_task(stream_app.run())
    logger.info("FastStream started")


@app.on_event("shutdown")
async def shutdown_event():
    task: asyncio.Task | None = getattr(app.state, "stream_task", None)
    if task:
        await stream_app.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("FastStream stopped")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=app_cfg.host, port=app_cfg.port, reload=False)
