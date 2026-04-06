import os
from functools import lru_cache
from pydantic_settings import BaseSettings


def _resolve_db_url() -> str:
    app_url = os.environ.get("APP_DATABASE_URL", "")
    if app_url:
        return app_url
    return "sqlite+aiosqlite:///./lingogenbot.db"


class Settings(BaseSettings):
    # Bot
    BOT_TOKEN: str = ""
    MONITOR_CHANNEL_ID: str = ""

    # Backend
    BACKEND_URL: str = "http://localhost:8000"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Database — read APP_DATABASE_URL; never collide with Replit's managed DATABASE_URL
    APP_DATABASE_URL: str = "sqlite+aiosqlite:///./lingogenbot.db"

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
        return self.APP_DATABASE_URL

    class Config:
        extra = "allow"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
