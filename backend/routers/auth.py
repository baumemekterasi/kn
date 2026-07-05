"""Auth router: login, logout, me, context (F0-A multi-entity identity).

Gelombang 3 SEC-1/SEC-2:
- bcrypt password hashing + migrasi transparan SHA256→bcrypt (rehash saat login sukses)
- session token 256-bit + TTL (index Mongo) + HttpOnly cookie (fallback Bearer tetap didukung)
- lockout brute-force: 5 percobaan gagal per IP+email → kunci 15 menit
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Request, Response
from pymongo import ReturnDocument
from db import db
from dependencies import current_user, audit, extract_token, session_expiry, SESSION_COOKIE
from core_utils import hash_password, verify_password, is_legacy_hash, new_id, now_iso, safe_doc, SESSION_TTL_HOURS
from schemas import LoginRequest
from services.entity_context_service import build_entity_context

router = APIRouter(prefix="/api")

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _check_lockout(identifier: str) -> None:
    rec = await db.login_attempts.find_one({"identifier": identifier})
    if not rec:
        return
    locked_until = rec.get("locked_until")
    if isinstance(locked_until, datetime) and not locked_until.tzinfo:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    if locked_until and locked_until > datetime.now(timezone.utc):
        sisa = int((locked_until - datetime.now(timezone.utc)).total_seconds() // 60) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Terlalu banyak percobaan login gagal. Coba lagi dalam {sisa} menit.")


async def _register_failure(identifier: str) -> None:
    rec = await db.login_attempts.find_one_and_update(
        {"identifier": identifier},
        {"$inc": {"count": 1}, "$set": {"last_attempt_at": datetime.now(timezone.utc)}},
        upsert=True, return_document=ReturnDocument.AFTER)
    if rec and rec.get("count", 0) >= MAX_LOGIN_ATTEMPTS:
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$set": {"locked_until": datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES),
                      "count": 0}})


@router.post("/auth/login")
async def login(payload: LoginRequest, request: Request, response: Response) -> Dict[str, Any]:
    email = (payload.email or "").strip()
    identifier = f"{_client_ip(request)}:{email.lower()}"
    await _check_lockout(identifier)
    user = safe_doc(await db.users.find_one({"email": email, "status": "active"}, {"_id": 0}))
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        await _register_failure(identifier)
        raise HTTPException(status_code=401, detail="Email atau password tidak sesuai")
    await db.login_attempts.delete_one({"identifier": identifier})
    if is_legacy_hash(user.get("password_hash", "")):
        # SEC-1 — migrasi transparan SHA256 → bcrypt saat login sukses
        await db.users.update_one({"id": user["id"]},
                                  {"$set": {"password_hash": hash_password(payload.password)}})
    token = secrets.token_urlsafe(32)  # SEC-2 — entropi 256-bit
    await db.sessions.insert_one(
        {"id": new_id("session"), "token": token, "user_id": user["id"],
         "created_at": now_iso(), "expires_at": session_expiry()})
    response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=False, samesite="lax",
                        max_age=SESSION_TTL_HOURS * 3600, path="/")
    user.pop("password_hash", None)
    await audit(user["name"], "login", "user", user["id"], {"email": user["email"], "role": user["role"]})
    onboarding = safe_doc(await db.user_onboarding.find_one({"user_id": user["id"]}, {"_id": 0}))
    entity_context = await build_entity_context(user)
    return {"token": token, "user": user, "onboarding": onboarding, "entity_context": entity_context}


@router.get("/auth/me")
async def me(request: Request) -> Dict[str, Any]:
    """User aktif + entity context (active = header X-Entity-Id bila valid)."""
    user = await current_user(request)
    requested = request.headers.get("X-Entity-Id")
    user["entity_context"] = await build_entity_context(user, requested)
    return user


@router.get("/auth/context")
async def auth_context(request: Request) -> Dict[str, Any]:
    """Entity context terpisah (dipakai Entity Switcher / refresh konteks)."""
    user = await current_user(request)
    requested = request.headers.get("X-Entity-Id")
    return await build_entity_context(user, requested)


@router.post("/auth/logout")
async def logout(request: Request, response: Response) -> Dict[str, str]:
    token = extract_token(request)
    if token:
        await db.sessions.delete_one({"token": token})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"message": "Logout berhasil"}
