from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from backend.app.models.user import User
from backend.app.models.session import Session, SessionStatus
from backend.app.models.anonymous_message import AnonymousMessage
from backend.app.models.moderation import ModerationFlag, AdminLog
from backend.app.models.profile import UserProfile
from backend.app.models.user_statistics import UserStatistics
from backend.app.schemas.admin import AdminDashboardStats, AdminUserDetail, AdminLogRead, ModerationFlagRead
from backend.app.core.logging_config import get_logger
from backend.app.core.redis_client import get_queue_length

logger = get_logger(__name__)


async def get_dashboard_stats(db: AsyncSession) -> AdminDashboardStats:
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_sessions = (await db.execute(select(func.count()).select_from(Session))).scalar_one()

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    active_users_today = (
        await db.execute(
            select(func.count()).select_from(User).where(User.last_seen >= today_start)
        )
    ).scalar_one()

    active_sessions = await get_queue_length()

    total_anon_msgs = (
        await db.execute(select(func.count()).select_from(AnonymousMessage))
    ).scalar_one()

    pending_flags = (
        await db.execute(
            select(func.count()).select_from(ModerationFlag).where(ModerationFlag.status == "pending")
        )
    ).scalar_one()

    top_xp = (
        await db.execute(select(func.max(UserProfile.xp)).select_from(UserProfile))
    ).scalar_one() or 0

    return AdminDashboardStats(
        total_users=total_users,
        active_users_today=active_users_today,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        total_anonymous_messages=total_anon_msgs,
        pending_moderation_flags=pending_flags,
        top_user_xp=top_xp,
    )


async def list_users(
    db: AsyncSession, limit: int = 50, offset: int = 0
) -> list[AdminUserDetail]:
    result = await db.execute(
        select(User).order_by(desc(User.last_seen)).limit(limit).offset(offset)
    )
    users = result.scalars().all()
    out: list[AdminUserDetail] = []
    for u in users:
        profile_res = await db.execute(
            select(UserProfile).where(UserProfile.telegram_id == u.telegram_id)
        )
        profile = profile_res.scalar_one_or_none()
        stats_res = await db.execute(
            select(UserStatistics).where(UserStatistics.telegram_id == u.telegram_id)
        )
        stats = stats_res.scalar_one_or_none()
        out.append(AdminUserDetail(
            telegram_id=u.telegram_id,
            username=u.username,
            first_name=u.first_name,
            is_active=u.is_active,
            created_at=u.created_at,
            last_seen=u.last_seen,
            xp=profile.xp if profile else 0,
            level=profile.level if profile else 1,
            reputation_score=profile.reputation_score if profile else 0.0,
            total_conversations=stats.total_conversations if stats else 0,
            avg_rating_received=stats.avg_rating_received if stats else 0.0,
        ))
    return out


async def perform_admin_action(
    db: AsyncSession,
    admin_id: int,
    target_id: int,
    action: str,
    reason: str | None = None,
) -> bool:
    result = await db.execute(select(User).where(User.telegram_id == target_id))
    user = result.scalar_one_or_none()
    if not user:
        return False

    if action == "suspend":
        user.is_active = False
    elif action == "unsuspend":
        user.is_active = True
    elif action == "reset_xp":
        profile_res = await db.execute(
            select(UserProfile).where(UserProfile.telegram_id == target_id)
        )
        profile = profile_res.scalar_one_or_none()
        if profile:
            profile.xp = 0
            profile.level = 1
    else:
        logger.warning(f"Unknown admin action '{action}'")
        return False

    log = AdminLog(
        admin_telegram_id=admin_id,
        action=action,
        target_type="user",
        target_id=str(target_id),
        details=reason,
    )
    db.add(log)
    await db.flush()
    logger.info(f"Admin {admin_id} performed '{action}' on user {target_id}")
    return True


async def get_pending_flags(
    db: AsyncSession, limit: int = 50
) -> list[ModerationFlagRead]:
    result = await db.execute(
        select(ModerationFlag)
        .where(ModerationFlag.status == "pending")
        .order_by(ModerationFlag.created_at)
        .limit(limit)
    )
    flags = result.scalars().all()
    return [ModerationFlagRead.model_validate(f) for f in flags]


async def resolve_flag(
    db: AsyncSession, flag_id: int, admin_id: int, action: str
) -> bool:
    """action: 'dismiss' or 'confirm'."""
    result = await db.execute(select(ModerationFlag).where(ModerationFlag.id == flag_id))
    flag = result.scalar_one_or_none()
    if not flag:
        return False
    flag.status = "dismissed" if action == "dismiss" else "reviewed"
    flag.reviewed_at = datetime.now(timezone.utc)

    log = AdminLog(
        admin_telegram_id=admin_id,
        action=f"flag_{action}",
        target_type="moderation_flag",
        target_id=str(flag_id),
    )
    db.add(log)
    await db.flush()
    return True


async def get_audit_log(
    db: AsyncSession, limit: int = 50
) -> list[AdminLogRead]:
    result = await db.execute(
        select(AdminLog).order_by(desc(AdminLog.created_at)).limit(limit)
    )
    logs = result.scalars().all()
    return [AdminLogRead.model_validate(lg) for lg in logs]
