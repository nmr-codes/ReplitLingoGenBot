import os
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.admin import AdminUserCreate, AdminUserRead, AdminLogRead, DashboardStats
from backend.app.schemas.user import UserRead
from backend.app.services.admin_service import (
    get_admin,
    create_admin,
    get_or_create_admin,
    get_dashboard_stats,
    list_users,
    block_user,
    unblock_user,
    get_recent_logs,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def _get_admin_secret() -> str:
    return os.environ.get("ADMIN_SECRET", "")


async def require_admin_key(key: str | None = Security(_api_key_header)) -> str:
    secret = _get_admin_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="Admin access is not configured")
    if not key or key != secret:
        raise HTTPException(status_code=403, detail="Invalid or missing admin key")
    return key


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin_key),
):
    return await get_dashboard_stats(db)


@router.get("/users", response_model=list[UserRead])
async def admin_list_users(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin_key),
):
    return await list_users(db, limit=limit, offset=offset)


@router.post("/users/{telegram_id}/block")
async def admin_block_user(
    telegram_id: int,
    admin_telegram_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin_key),
):
    ok = await block_user(db, admin_telegram_id, telegram_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "action": "blocked", "user": telegram_id}


@router.post("/users/{telegram_id}/unblock")
async def admin_unblock_user(
    telegram_id: int,
    admin_telegram_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin_key),
):
    ok = await unblock_user(db, admin_telegram_id, telegram_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "action": "unblocked", "user": telegram_id}


@router.get("/logs", response_model=list[AdminLogRead])
async def admin_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin_key),
):
    return await get_recent_logs(db, limit=limit)


@router.post("/admins", response_model=AdminUserRead)
async def add_admin(
    data: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin_key),
):
    admin = await get_or_create_admin(db, data)
    return admin
