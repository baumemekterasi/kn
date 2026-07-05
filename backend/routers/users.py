"""Users router: CRUD users."""
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Request
from pymongo import ReturnDocument
from db import db
from dependencies import require_permission, audit
from core_utils import hash_password, new_id, now_iso, safe_doc
from schemas import GenericPatch, UserCreate
from services.entity_context_service import (
    PRIMARY_ENTITY_ID, resolve_allowed_entities, all_active_entity_ids,
)

router = APIRouter(prefix="/api")


@router.get("/users")
async def list_users(request: Request) -> List[Dict[str, Any]]:
    await require_permission(request, "user", "view")
    return await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(100)


@router.post("/users")
async def create_user(payload: UserCreate, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "user", "create")
    if await db.users.find_one({"email": payload.email}, {"_id": 0}):
        raise HTTPException(status_code=409, detail="Email user sudah terdaftar")
    # F6 — multi-entitas: home_entity_id + allowed_entity_ids (resolve default bila kosong).
    all_ids = await all_active_entity_ids() or [PRIMARY_ENTITY_ID]
    home = (payload.home_entity_id or "").strip() or PRIMARY_ENTITY_ID
    if home not in all_ids:
        raise HTTPException(status_code=400, detail="home_entity_id tidak valid.")
    allowed = [e for e in (payload.allowed_entity_ids or []) if e in all_ids]
    if not allowed:
        allowed = resolve_allowed_entities(payload.role, home, all_ids)
    if home not in allowed:
        allowed = [home] + allowed
    user = {
        "id": new_id("user"),
        "name": payload.name,
        "email": payload.email,
        "role": payload.role,
        "password_hash": hash_password(payload.password),
        "home_entity_id": home,
        "allowed_entity_ids": allowed,
        "status": "active",
        "created_at": now_iso(),
    }
    await db.users.insert_one(user)
    await audit(actor["name"], "user_created", "user", user["id"],
                {k: v for k, v in user.items() if k != "password_hash"})
    user.pop("password_hash", None)
    return safe_doc(user)


@router.patch("/users/{user_id}")
async def update_user(user_id: str, payload: GenericPatch, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "user", "update")
    data = {k: v for k, v in payload.data.items() if k in ["name", "email", "role", "status", "home_entity_id", "allowed_entity_ids"]}
    # F6 — validasi entitas bila diubah.
    if "home_entity_id" in data or "allowed_entity_ids" in data:
        all_ids = await all_active_entity_ids() or [PRIMARY_ENTITY_ID]
        if "home_entity_id" in data and data["home_entity_id"] not in all_ids:
            raise HTTPException(status_code=400, detail="home_entity_id tidak valid.")
        if "allowed_entity_ids" in data:
            data["allowed_entity_ids"] = [e for e in (data["allowed_entity_ids"] or []) if e in all_ids]
    if "password" in payload.data and payload.data["password"]:
        data["password_hash"] = hash_password(payload.data["password"])
    data["updated_at"] = now_iso()
    user = await db.users.find_one_and_update(
        {"id": user_id}, {"$set": data},
        projection={"_id": 0, "password_hash": 0},
        return_document=ReturnDocument.AFTER
    )
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    await audit(actor["name"], "user_updated", "user", user_id, user)
    return user
