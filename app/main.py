import asyncio
import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.worker import transcription_worker
from app.routers import transcriptions, files


def _setup_logging() -> None:
    log_path = settings.data_dir / "app.log"
    handlers = [
        RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"),
        logging.StreamHandler(),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    _setup_logging()
    await init_db()
    worker_task = asyncio.create_task(transcription_worker())
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Class Transcriber", lifespan=lifespan)

app.include_router(transcriptions.router)
app.include_router(files.router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/transcripciones")
