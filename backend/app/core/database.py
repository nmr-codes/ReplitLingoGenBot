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
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_pre_ping=True,
        )
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
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified successfully.")
