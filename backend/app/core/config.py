import os
from functools import lru_cache
from pydantic_settings import BaseSettings


def _resolve_database_url() -> str:
    on_render = bool(os.environ.get("RENDER"))

    if on_render:
        raw = os.environ.get("DATABASE_URL", "")
        if raw.startswith("postgres://"):
            return raw.replace("postgres://", "postgresql+asyncpg://", 1)
        if raw.startswith("postgresql://") and "+asyncpg" not in raw:
            return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
        if raw:
            return raw

    app_url = os.environ.get("APP_DATABASE_URL", "")
    if app_url:
        if app_url.startswith("postgres://"):
            return app_url.replace("postgres://", "postgresql+asyncpg://", 1)
        if app_url.startswith("postgresql://") and "+asyncpg" not in app_url:
            return app_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return app_url

    return "sqlite+aiosqlite:///./lingogenbot.db"


def _resolve_backend_url() -> str:
    raw = os.environ.get("BACKEND_URL", "")
    if not raw:
        return "http://localhost:8000"
    if raw.startswith(("http://", "https://")):
        return raw.rstrip("/")
    return f"https://{raw.rstrip('/')}"


class Settings(BaseSettings):
    # Bot
    BOT_TOKEN: str = ""
    MONITOR_CHANNEL_ID: str = ""

    # Backend — Render injects PORT automatically for web services
    API_HOST: str = "0.0.0.0"
    API_PORT: int = int(os.environ.get("PORT", os.environ.get("API_PORT", "8000")))

    # Redis
    REDIS_URL: str = "fakeredis://"

    # Matchmaking
    MATCH_TIMEOUT_SECONDS: int = 120
    SESSION_DURATION_SECONDS: int = 300
    SEARCH_UPDATE_INTERVAL: int = 15

    # App
    DEBUG: bool = False
    APP_NAME: str = "LingoGenBot"
    VERSION: str = "1.0.0"

    @property
    def DATABASE_URL(self) -> str:
        return _resolve_database_url()

    @property
    def BACKEND_URL(self) -> str:
        return _resolve_backend_url()

    class Config:
        extra = "allow"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
