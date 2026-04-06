from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)

_engine = None
_AsyncSessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        from backend.app.core.config import settings
        db_url = settings.DATABASE_URL
        is_sqlite = db_url.startswith("sqlite")

        kwargs: dict = {"echo": settings.DEBUG, "pool_pre_ping": True}
        if not is_sqlite:
            kwargs["pool_size"] = 5
            kwargs["max_overflow"] = 5

        _engine = create_async_engine(db_url, **kwargs)
    return _engine


def _get_session_factory():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _AsyncSessionLocal


class Base(DeclarativeBase):
    pass


async def get_db():
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    from backend.app.models import user, session, rating  # noqa: F401
    from backend.app.models import profile  # noqa: F401
    from backend.app.models import admin  # noqa: F401
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified successfully.")
