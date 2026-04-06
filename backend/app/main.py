import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from backend.app.core.config import settings
from backend.app.core.logging_config import setup_logging, get_logger
from backend.app.core.database import init_db
from backend.app.core.redis_client import get_redis, close_redis
from backend.app.api.routers import users, matchmaking, sessions, profiles, messages, admin

setup_logging()
logger = get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    await init_db()
    try:
        await get_redis()
    except Exception as e:
        logger.error(f"Redis connection failed at startup: {e}. Continuing — will retry on first use.")
    yield
    await close_redis()
    logger.info("Application shutdown complete.")


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
app.include_router(messages.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


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


@app.get("/chat/{slug}", response_class=HTMLResponse)
async def anonymous_message_page(request: Request, slug: str):
    """Public web page where anyone can send an anonymous message to a profile."""
    from backend.app.core.database import _get_session_factory
    from backend.app.services.profile_service import get_profile_by_slug

    factory = _get_session_factory()
    async with factory() as db:
        profile = await get_profile_by_slug(db, slug)
        if not profile or not profile.is_public:
            return HTMLResponse(
                content=(
                    "<html><body style='font-family:sans-serif;text-align:center;padding:4rem'>"
                    "<h2>Profile not found</h2>"
                    "<p>This profile does not exist or is private.</p>"
                    "</body></html>"
                ),
                status_code=404,
            )
        return templates.TemplateResponse(
            request,
            "anon_message.html",
            {
                "profile_slug": slug,
                "display_name": profile.display_name or "Anonymous User",
                "bio": profile.bio,
                "language_level": profile.language_level,
            },
        )


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request):
    """Admin dashboard web interface."""
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
    )
