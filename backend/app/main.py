import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.logging_config import setup_logging, get_logger
from backend.app.core.database import init_db
from backend.app.core.redis_client import get_redis, close_redis
from backend.app.api.routers import (
    users,
    matchmaking,
    sessions,
    profiles,
    anonymous_messages,
    admin,
    leaderboard,
    channels,
)

from backend.bot.bot import main

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.VERSION}")
    await init_db()
    try:
        await get_redis()
    except Exception as e:
        logger.error(f"Redis connection failed at startup: {e}. Continuing — will retry on first use.")

    bot_task = asyncio.create_task(main())
    logger.info("🤖 Bot polling started alongside the API.")

    yield

    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass

    await close_redis()
    logger.info("✅ Application shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Backend API for LingoGenBot – anonymous English practice via Telegram",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(users.router, prefix="/api/v1")
app.include_router(matchmaking.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(anonymous_messages.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(leaderboard.router, prefix="/api/v1")
app.include_router(channels.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.VERSION}
    
@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
    }
