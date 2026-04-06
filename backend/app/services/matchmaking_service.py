import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.redis_client import (
    enqueue_user, dequeue_user, remove_from_queue, get_queue_length,
    set_search_state, get_search_state, clear_search_state,
    set_user_session, get_user_session, clear_user_session,
    set_session_data, get_session_data, clear_session_data,
)
from backend.app.models.session import Session, SessionStatus
from backend.app.schemas.session import MatchResponse, SessionCreate
from backend.app.services.topics import get_random_topic
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)


async def request_match(db: AsyncSession, telegram_id: int) -> MatchResponse:
    existing_session = await get_user_session(telegram_id)
    if existing_session:
        logger.warning(f"User {telegram_id} already in session {existing_session}")
        return MatchResponse(
            matched=True,
            session_uuid=existing_session,
            message="You are already in an active session.",
        )

    existing_state = await get_search_state(telegram_id)
    if existing_state:
        logger.info(f"User {telegram_id} already searching.")
        return MatchResponse(
            matched=False,
            queue_position=await get_queue_length(),
            message="Already searching for a partner.",
        )

    partner_id = await dequeue_user()

    if partner_id and partner_id != telegram_id:
        session_uuid = str(uuid.uuid4())
        topic = get_random_topic()

        session = Session(
            session_uuid=session_uuid,
            user1_id=partner_id,
            user2_id=telegram_id,
            topic=topic,
            status=SessionStatus.ACTIVE,
        )
        db.add(session)
        await db.flush()

        session_data = {
            "user1_id": partner_id,
            "user2_id": telegram_id,
            "topic": topic,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        await set_session_data(session_uuid, session_data)
        await set_user_session(partner_id, session_uuid)
        await set_user_session(telegram_id, session_uuid)
        await clear_search_state(partner_id)
        await clear_search_state(telegram_id)

        logger.info(f"Match found: {partner_id} <-> {telegram_id}, session={session_uuid}, topic={topic}")

        return MatchResponse(
            matched=True,
            session_uuid=session_uuid,
            partner_id=partner_id,
            topic=topic,
            message=f"Partner found! Topic: {topic}",
        )

    if partner_id == telegram_id:
        await enqueue_user(partner_id)

    await enqueue_user(telegram_id)
    await set_search_state(telegram_id, {
        "status": "searching",
        "started_at": datetime.now(timezone.utc).isoformat(),
    })

    queue_len = await get_queue_length()
    logger.info(f"User {telegram_id} enqueued. Queue length: {queue_len}")

    return MatchResponse(
        matched=False,
        queue_position=queue_len,
        message="Searching for a partner... Please wait.",
    )


async def cancel_search(telegram_id: int) -> bool:
    await remove_from_queue(telegram_id)
    await clear_search_state(telegram_id)
    logger.info(f"User {telegram_id} cancelled search.")
    return True


async def end_session(db: AsyncSession, session_uuid: str, status: SessionStatus = SessionStatus.ENDED) -> Session | None:
    result = await db.execute(
        select(Session).where(Session.session_uuid == session_uuid)
    )
    session = result.scalar_one_or_none()

    if not session:
        logger.warning(f"Session {session_uuid} not found for ending.")
        return None

    now = datetime.now(timezone.utc)
    session.status = status
    session.end_time = now
    if session.start_time:
        start = session.start_time
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        delta = now - start
        session.duration_seconds = int(delta.total_seconds())

    await db.flush()

    data = await get_session_data(session_uuid)
    if data:
        user1_id = int(data.get("user1_id", 0))
        user2_id = int(data.get("user2_id", 0))
        if user1_id:
            await clear_user_session(user1_id)
        if user2_id:
            await clear_user_session(user2_id)

        # Update statistics and XP for both participants
        duration = session.duration_seconds or 0
        for uid in [uid for uid in [user1_id, user2_id] if uid]:
            try:
                from backend.app.services.statistics_service import record_conversation_completed
                from backend.app.services.profile_service import add_xp, update_streak
                from backend.app.services.achievement_service import check_and_award_achievements
                await record_conversation_completed(db, uid, duration)
                await add_xp(db, uid, 10)  # XP per completed conversation
                await update_streak(db, uid)
                await check_and_award_achievements(db, uid)
            except Exception as e:
                logger.error(f"Failed to update stats for user {uid} after session end: {e}")

    await clear_session_data(session_uuid)

    logger.info(f"Session {session_uuid} ended with status={status}")
    return session


async def get_session_partner(session_uuid: str, telegram_id: int) -> int | None:
    data = await get_session_data(session_uuid)
    if not data:
        return None
    user1 = int(data.get("user1_id", 0))
    user2 = int(data.get("user2_id", 0))
    if user1 == telegram_id:
        return user2
    if user2 == telegram_id:
        return user1
    return None
