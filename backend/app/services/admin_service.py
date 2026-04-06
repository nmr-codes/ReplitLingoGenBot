from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.models.admin import AdminUser, AdminLog, AnonymousMessage
from backend.app.models.user import User
from backend.app.models.profile import UserProfile
from backend.app.models.session import Session as ChatSession
from backend.app.schemas.admin import AdminUserCreate, DashboardStats
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)


async def get_admin(db: AsyncSession, telegram_id: int) -> AdminUser | None:
    result = await db.execute(
        select(AdminUser).where(
            AdminUser.telegram_id == telegram_id,
            AdminUser.is_active == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def create_admin(db: AsyncSession, data: AdminUserCreate) -> AdminUser:
    admin = AdminUser(
        telegram_id=data.telegram_id,
        username=data.username,
        role=data.role,
    )
    db.add(admin)
    await db.flush()
    logger.info(f"Created admin user {data.telegram_id} with role {data.role}")
    return admin


async def get_or_create_admin(db: AsyncSession, data: AdminUserCreate) -> AdminUser:
    admin = await get_admin(db, data.telegram_id)
    if admin:
        return admin
    return await create_admin(db, data)


async def log_admin_action(
    db: AsyncSession,
    admin_telegram_id: int,
    action: str,
    target_telegram_id: int | None = None,
    details: str | None = None,
) -> AdminLog:
    entry = AdminLog(
        admin_telegram_id=admin_telegram_id,
        action=action,
        target_telegram_id=target_telegram_id,
        details=details,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_dashboard_stats(db: AsyncSession) -> DashboardStats:
    total_users_result = await db.execute(select(func.count(User.telegram_id)))
    total_users = total_users_result.scalar_one() or 0

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    active_today_result = await db.execute(
        select(func.count(User.telegram_id)).where(User.last_seen >= today)
    )
    active_users_today = active_today_result.scalar_one() or 0

    total_sessions_result = await db.execute(select(func.count(ChatSession.session_uuid)))
    total_sessions = total_sessions_result.scalar_one() or 0

    active_sessions_result = await db.execute(
        select(func.count(ChatSession.session_uuid)).where(ChatSession.status == "active")
    )
    active_sessions = active_sessions_result.scalar_one() or 0

    total_profiles_result = await db.execute(select(func.count(UserProfile.id)))
    total_profiles = total_profiles_result.scalar_one() or 0

    total_msgs_result = await db.execute(select(func.count(AnonymousMessage.id)))
    total_anonymous_messages = total_msgs_result.scalar_one() or 0

    unread_msgs_result = await db.execute(
        select(func.count(AnonymousMessage.id)).where(AnonymousMessage.is_read == False)  # noqa: E712
    )
    unread_anonymous_messages = unread_msgs_result.scalar_one() or 0

    return DashboardStats(
        total_users=total_users,
        active_users_today=active_users_today,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        total_profiles=total_profiles,
        total_anonymous_messages=total_anonymous_messages,
        unread_anonymous_messages=unread_anonymous_messages,
    )


async def list_users(
    db: AsyncSession, limit: int = 50, offset: int = 0
) -> list[User]:
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def block_user(
    db: AsyncSession, admin_telegram_id: int, target_telegram_id: int
) -> bool:
    result = await db.execute(
        select(User).where(User.telegram_id == target_telegram_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return False
    user.is_active = False
    await log_admin_action(
        db,
        admin_telegram_id=admin_telegram_id,
        action="BLOCK_USER",
        target_telegram_id=target_telegram_id,
    )
    await db.flush()
    return True


async def unblock_user(
    db: AsyncSession, admin_telegram_id: int, target_telegram_id: int
) -> bool:
    result = await db.execute(
        select(User).where(User.telegram_id == target_telegram_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return False
    user.is_active = True
    await log_admin_action(
        db,
        admin_telegram_id=admin_telegram_id,
        action="UNBLOCK_USER",
        target_telegram_id=target_telegram_id,
    )
    await db.flush()
    return True


async def get_recent_logs(
    db: AsyncSession, limit: int = 50
) -> list[AdminLog]:
    result = await db.execute(
        select(AdminLog).order_by(AdminLog.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
