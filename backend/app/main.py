import asyncio, logging, uvicorn
from fastapi import FastAPI
from app.config import app_cfg
from app.broker import app as stream_app
import app.consumers  # noqa: F401
from app.api.routes import router as api_router
from database import db

logging.basicConfig(level=getattr(logging, app_cfg.log_level.upper(), logging.INFO),
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

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
    uvicorn.run("app.main:app", host=app_cfg.host, port=app_cfg.port, reload=False)
