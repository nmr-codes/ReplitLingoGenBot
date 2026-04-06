from __future__ import annotations

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)

_redis = None

QUEUE_KEY = "matchmaking:queue"
SESSION_KEY_PREFIX = "session:"
SEARCH_STATE_PREFIX = "search_state:"
USER_SESSION_PREFIX = "user_session:"


async def get_redis():
    global _redis
    if _redis is not None:
        return _redis

    if settings.REDIS_URL.startswith("fakeredis"):
        from fakeredis import aioredis as fakeredis_aio
        _redis = fakeredis_aio.FakeRedis(decode_responses=True)
        logger.info("Using FakeRedis for local development.")
    else:
        from redis.asyncio import from_url
        _redis = from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("Redis connection established.")

    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        try:
            await _redis.aclose()
        except Exception:
            pass
        _redis = None
        logger.info("Redis connection closed.")


async def enqueue_user(user_id: int) -> None:
    r = await get_redis()
    await r.rpush(QUEUE_KEY, str(user_id))


async def dequeue_user() -> int | None:
    r = await get_redis()
    val = await r.lpop(QUEUE_KEY)
    return int(val) if val else None


async def remove_from_queue(user_id: int) -> None:
    r = await get_redis()
    await r.lrem(QUEUE_KEY, 0, str(user_id))


async def get_queue_length() -> int:
    r = await get_redis()
    return await r.llen(QUEUE_KEY)


async def set_search_state(user_id: int, data: dict) -> None:
    r = await get_redis()
    key = f"{SEARCH_STATE_PREFIX}{user_id}"
    await r.hset(key, mapping={k: str(v) for k, v in data.items()})
    await r.expire(key, 300)


async def get_search_state(user_id: int) -> dict | None:
    r = await get_redis()
    key = f"{SEARCH_STATE_PREFIX}{user_id}"
    data = await r.hgetall(key)
    return data if data else None


async def clear_search_state(user_id: int) -> None:
    r = await get_redis()
    await r.delete(f"{SEARCH_STATE_PREFIX}{user_id}")


async def set_user_session(user_id: int, session_id: str) -> None:
    r = await get_redis()
    key = f"{USER_SESSION_PREFIX}{user_id}"
    await r.set(key, session_id, ex=3600)


async def get_user_session(user_id: int) -> str | None:
    r = await get_redis()
    return await r.get(f"{USER_SESSION_PREFIX}{user_id}")


async def clear_user_session(user_id: int) -> None:
    r = await get_redis()
    await r.delete(f"{USER_SESSION_PREFIX}{user_id}")


async def set_session_data(session_id: str, data: dict) -> None:
    r = await get_redis()
    key = f"{SESSION_KEY_PREFIX}{session_id}"
    await r.hset(key, mapping={k: str(v) for k, v in data.items()})
    await r.expire(key, 3600)


async def get_session_data(session_id: str) -> dict | None:
    r = await get_redis()
    key = f"{SESSION_KEY_PREFIX}{session_id}"
    data = await r.hgetall(key)
    return data if data else None


async def clear_session_data(session_id: str) -> None:
    r = await get_redis()
    await r.delete(f"{SESSION_KEY_PREFIX}{session_id}")
