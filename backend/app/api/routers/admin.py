from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.schemas.admin import (
    AdminDashboardStats, AdminActionRequest, AdminUserDetail,
    ModerationFlagRead, AdminLogRead
)
from backend.app.services.admin_service import (
    get_dashboard_stats, list_users, perform_admin_action,
    get_pending_flags, resolve_flag, get_audit_log
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(x_admin_id: Annotated[str | None, Header(alias="X-Admin-Id")] = None) -> int:
    """Simple header-based admin auth: X-Admin-Id must match a configured admin Telegram ID."""
    if not x_admin_id:
        raise HTTPException(status_code=401, detail="Missing X-Admin-Id header")
    try:
        admin_id = int(x_admin_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-Admin-Id")
    if admin_id not in settings.admin_ids:
        raise HTTPException(status_code=403, detail="Not authorized as admin")
    return admin_id


@router.get("/dashboard", response_model=AdminDashboardStats)
async def admin_dashboard(
    admin_id: int = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_dashboard_stats(db)


@router.get("/users", response_model=list[AdminUserDetail])
async def admin_users(
    limit: int = 50,
    offset: int = 0,
    admin_id: int = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await list_users(db, limit=limit, offset=offset)


@router.post("/action")
async def admin_action(
    data: AdminActionRequest,
    admin_id: int = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    if admin_id != data.admin_telegram_id:
        raise HTTPException(status_code=403, detail="Admin ID mismatch")
    ok = await perform_admin_action(db, admin_id, data.target_telegram_id, data.action, data.reason)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found or unknown action")
    return {"status": "ok", "action": data.action, "target": data.target_telegram_id}


@router.get("/flags", response_model=list[ModerationFlagRead])
async def admin_flags(
    admin_id: int = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_pending_flags(db)


@router.post("/flags/{flag_id}/resolve")
async def admin_resolve_flag(
    flag_id: int,
    action: str,
    admin_id: int = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    if action not in {"dismiss", "confirm"}:
        raise HTTPException(status_code=400, detail="action must be 'dismiss' or 'confirm'")
    ok = await resolve_flag(db, flag_id, admin_id, action)
    if not ok:
        raise HTTPException(status_code=404, detail="Flag not found")
    return {"status": "ok"}


@router.get("/audit-log", response_model=list[AdminLogRead])
async def admin_audit_log(
    limit: int = 50,
    admin_id: int = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_audit_log(db, limit=limit)
