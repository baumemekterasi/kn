"""Warehouses router: CRUD warehouses + geolocation + lokasi (Zone→Rack→Level→Bin)."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from pymongo import ReturnDocument
from db import db
from dependencies import require_permission, audit
from core_utils import new_id, now_iso, safe_doc
from entity_scope import entity_ctx
from schemas import GenericPatch, WarehousePayload
from services.location_service import warehouse_locations, save_warehouse_structure

router = APIRouter(prefix="/api")


class StructurePayload(BaseModel):
    zones: List[Dict[str, Any]] = []


@router.get("/warehouses/{warehouse_id}/locations")
async def get_warehouse_locations(warehouse_id: str, request: Request, entity_id: Optional[str] = None) -> Dict[str, Any]:
    """Fase 5 — hierarki lokasi + okupansi/utilisasi per bin (entity-scoped)."""
    await require_permission(request, "warehouse", "view")
    ctx = await entity_ctx(request)
    return await warehouse_locations(warehouse_id, ctx, entity_id)


@router.put("/warehouses/{warehouse_id}/structure")
async def put_warehouse_structure(warehouse_id: str, payload: StructurePayload, request: Request) -> Dict[str, Any]:
    """Simpan struktur Zone→Rack→Level→Bin (node baru otomatis diberi id, kode bin wajib unik)."""
    actor = await require_permission(request, "warehouse", "update")
    wh = await save_warehouse_structure(warehouse_id, payload.zones)
    await audit(actor["name"], "warehouse_structure_updated", "warehouse", warehouse_id,
                {"zones": len(payload.zones)})
    return safe_doc(wh)


@router.get("/warehouses")
async def list_warehouses() -> List[Dict[str, Any]]:
    return await db.warehouses.find({}, {"_id": 0}).to_list(100)


@router.post("/warehouses")
async def create_warehouse(payload: WarehousePayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "warehouse", "create")
    if await db.warehouses.find_one({"code": payload.code}, {"_id": 0}):
        raise HTTPException(status_code=409, detail="Kode gudang sudah digunakan")
    warehouse_id = new_id("wh")
    zone_id = new_id("zone")
    rack_id = new_id("rack")
    bin_id = new_id("bin")
    warehouse = {
        "id": warehouse_id,
        "code": payload.code,
        "name": payload.name,
        "city": payload.city,
        "lat": payload.lat,
        "lng": payload.lng,
        "zones": [{"id": zone_id, "name": "Zone A", "racks": [{"id": rack_id, "name": "Rack A1",
                    "bins": [{"id": bin_id, "code": payload.bin_code, "capacity": payload.bin_capacity}]}]}],
        "active": True,
        "created_at": now_iso(),
    }
    await db.warehouses.insert_one(warehouse)
    await audit(actor["name"], "warehouse_created", "warehouse", warehouse_id, warehouse)
    return safe_doc(warehouse)


@router.patch("/warehouses/{warehouse_id}")
async def update_warehouse(warehouse_id: str, payload: GenericPatch, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "warehouse", "update")
    allowed = ["code", "name", "city", "zones", "active", "lat", "lng"]
    data = {k: v for k, v in payload.data.items() if k in allowed}
    if data.get("code"):
        duplicate = await db.warehouses.find_one(
            {"code": data["code"], "id": {"$ne": warehouse_id}}, {"_id": 0}
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="Kode gudang sudah digunakan")
    data["updated_at"] = now_iso()
    warehouse = await db.warehouses.find_one_and_update(
        {"id": warehouse_id}, {"$set": data},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER
    )
    if not warehouse:
        raise HTTPException(status_code=404, detail="Gudang tidak ditemukan")
    await audit(actor["name"], "warehouse_updated", "warehouse", warehouse_id, warehouse)
    return warehouse


@router.delete("/warehouses/{warehouse_id}")
async def delete_warehouse(warehouse_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "warehouse", "delete")
    warehouse = await db.warehouses.find_one_and_update(
        {"id": warehouse_id},
        {"$set": {"active": False, "updated_at": now_iso()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER
    )
    if not warehouse:
        raise HTTPException(status_code=404, detail="Gudang tidak ditemukan")
    await audit(actor["name"], "warehouse_deactivated", "warehouse", warehouse_id, warehouse)
    return warehouse
