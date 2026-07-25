import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.routers import papers
from app.routes.chat import router as chat_router
from app.routes.metrics import router as metrics_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting Paper Pilot backend…")
    if engine is not None:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection verified.")
        except Exception as exc:
            logger.warning("Database not available at startup: %s", exc)
    else:
        logger.info("No DATABASE_URL configured — skipping DB check on startup.")
    yield
    logger.info("Shutting down Paper Pilot backend…")
    if engine is not None:
        await engine.dispose()


app = FastAPI(title="Paper Pilot API", version="0.1.0", lifespan=lifespan)

origins = [settings.FRONTEND_URL] if settings.FRONTEND_URL else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(papers.router)
app.include_router(chat_router)
app.include_router(metrics_router)


@app.get("/health")
async def health_check() -> dict:
    if engine is None:
        return {"status": "error", "db": "not_configured"}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        logger.exception("Health check failed")
        return {"status": "error", "db": "disconnected"}
