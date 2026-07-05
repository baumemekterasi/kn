"""Shared auth/permission dependencies and audit helper."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, Request
from db import db
from core_utils import safe_doc, now_iso, new_id, SESSION_TTL_HOURS
from permissions_config import DEFAULT_PERMISSIONS

SESSION_COOKIE = "session_token"


def session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)


def _as_utc(dt: Any) -> Optional[datetime]:
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def extract_token(request: Request) -> str:
    """SEC-2 — HttpOnly cookie diutamakan; fallback header Bearer (kompat)."""
    token = request.cookies.get(SESSION_COOKIE) or ""
    if not token:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header.replace("Bearer ", "").strip()
    return token


async def current_user(request: Request) -> Dict[str, Any]:
    token = extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Login diperlukan")
    session = await db.sessions.find_one({"token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Session tidak valid")
    now = datetime.now(timezone.utc)
    expires_at = _as_utc(session.get("expires_at"))
    if expires_at is None:
        # sesi pra-TTL: beri masa berlaku agar ikut kebijakan kedaluwarsa
        await db.sessions.update_one({"token": token}, {"$set": {"expires_at": session_expiry()}})
    elif expires_at <= now:
        await db.sessions.delete_one({"token": token})
        raise HTTPException(status_code=401, detail="Session kedaluwarsa — silakan login ulang")
    elif (expires_at - now) < timedelta(hours=SESSION_TTL_HOURS / 2):
        # sliding renewal: perpanjang saat sisa < setengah TTL
        await db.sessions.update_one({"token": token}, {"$set": {"expires_at": session_expiry()}})
    user = safe_doc(await db.users.find_one({"id": session["user_id"], "status": "active"}, {"_id": 0, "password_hash": 0}))
    if not user:
        raise HTTPException(status_code=401, detail="User tidak aktif")
    return user


async def require_role(request: Request, allowed_roles: List[str]) -> Dict[str, Any]:
    user = await current_user(request)
    if user.get("role") == "admin" or user.get("role") in allowed_roles:
        return user
    raise HTTPException(status_code=403, detail="Role Anda tidak memiliki izin untuk aksi ini")


async def permission_matrix() -> Dict[str, Dict[str, List[str]]]:
    record = safe_doc(await db.permission_settings.find_one({"id": "default"}, {"_id": 0}))
    return record.get("matrix", DEFAULT_PERMISSIONS) if record else DEFAULT_PERMISSIONS


async def require_permission(request: Request, module: str, action: str) -> Dict[str, Any]:
    user = await current_user(request)
    matrix = await permission_matrix()
    allowed = matrix.get(user.get("role"), {}).get(module, [])
    if action in allowed or "*" in allowed:
        return user
    raise HTTPException(status_code=403, detail=f"Permission ditolak: {module}.{action}")


async def audit(
    actor: str, action: str, entity_type: str, entity_id: str, after: Any, reason: str = ""
) -> None:
    # Clean after data to remove any MongoDB ObjectIds recursively
    clean_after = safe_doc(after) if after is not None else None
    await db.audit_logs.insert_one(
        {
            "id": new_id("audit"),
            "actor": actor,
            "role": "system/demo",
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "before": None,
            "after": clean_after,
            "reason": reason,
            "timestamp": now_iso(),
        }
    )
