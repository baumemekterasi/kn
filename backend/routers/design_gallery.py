"""HRD H5 router — Design Gallery (motif kain) + upload gambar + AI auto-tag.

Koleksi kanonik (entity-scoped): design_gallery (dsgn_). Keputusan owner 3a.
RBAC: read list/detail/file = hr.view; create/update/delete/upload/autotag = hr.manage_attendance.
Auto-tag AI (Claude) GRACEFUL: bila key kosong → 200 {enabled:false} (BUKAN error).

Path aksi pakai segmen literal (/files, /autotag) agar verify_api_contract 0 ERROR.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request, Query, UploadFile, File
from fastapi.responses import Response

from dependencies import require_permission, audit
from entity_scope import entity_ctx, resolve_list_scope, assert_entity_access
from schemas_design_gallery import GalleryInput, GalleryUpdate
from services import design_gallery_service as gallery

router = APIRouter(prefix="/api")


async def _guard(gallery_id: str, ctx) -> Dict[str, Any]:
    doc = await gallery.get_gallery(gallery_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entri galeri tidak ditemukan.")
    assert_entity_access(doc, "design_gallery", ctx)
    return doc


@router.get("/design-gallery")
async def list_gallery(request: Request, entity_id: Optional[str] = Query(None),
                       tag: Optional[str] = Query(None),
                       q: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    await require_permission(request, "hr", "view")
    ctx = await entity_ctx(request)
    scope = resolve_list_scope("design_gallery", {}, ctx, entity_id)
    return await gallery.list_gallery(scope, tag, q)


@router.post("/design-gallery")
async def create_gallery(payload: GalleryInput, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "hr", "manage_attendance")
    ctx = await entity_ctx(request)
    try:
        doc = await gallery.create_gallery(payload.model_dump(), actor["name"], ctx.active_entity_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_gallery_create", "design_gallery", doc["id"],
                {"title": doc["title"]})
    return doc


@router.get("/design-gallery/{gallery_id}")
async def get_gallery(gallery_id: str, request: Request) -> Dict[str, Any]:
    await require_permission(request, "hr", "view")
    ctx = await entity_ctx(request)
    return await _guard(gallery_id, ctx)


@router.put("/design-gallery/{gallery_id}")
async def update_gallery(gallery_id: str, payload: GalleryUpdate, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "hr", "manage_attendance")
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    patch = payload.model_dump(exclude_unset=True)
    try:
        doc = await gallery.update_gallery(gallery_id, patch)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_gallery_update", "design_gallery", gallery_id, patch)
    return doc


@router.delete("/design-gallery/{gallery_id}")
async def delete_gallery(gallery_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "hr", "manage_attendance")
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        res = await gallery.delete_gallery(gallery_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_gallery_delete", "design_gallery", gallery_id, {})
    return res


# ─── Files (upload / serve / delete) ──────────────────────────────────
@router.post("/design-gallery/{gallery_id}/files")
async def upload_gallery_file(gallery_id: str, request: Request,
                              file: UploadFile = File(...)) -> Dict[str, Any]:
    actor = await require_permission(request, "hr", "manage_attendance")
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    data = await file.read()
    try:
        fmeta = await gallery.add_file(gallery_id, file.filename or "motif",
                                       file.content_type or "", data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_gallery_upload", "design_gallery", gallery_id,
                {"file": fmeta.get("filename")})
    return fmeta


@router.get("/design-gallery/{gallery_id}/files/{file_id}")
async def get_gallery_file(gallery_id: str, file_id: str, request: Request):
    await require_permission(request, "hr", "view")
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        data, ctype = await gallery.get_file_bytes(gallery_id, file_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File fisik tidak ditemukan.")
    return Response(content=data, media_type=ctype,
                    headers={"Cache-Control": "private, max-age=300"})


@router.delete("/design-gallery/{gallery_id}/files/{file_id}")
async def delete_gallery_file(gallery_id: str, file_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "hr", "manage_attendance")
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        res = await gallery.delete_file(gallery_id, file_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await audit(actor["name"], "design_gallery_delete_file", "design_gallery", gallery_id,
                {"file_id": file_id})
    return res


# ─── AI auto-tag (graceful) ─────────────────────────────────────
@router.post("/design-gallery/{gallery_id}/autotag")
async def autotag_gallery(gallery_id: str, request: Request) -> Dict[str, Any]:
    """Trigger AI auto-tag. Bila AI nonaktif → 200 {enabled:false} (BUKAN error)."""
    actor = await require_permission(request, "hr", "manage_attendance")
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        res = await gallery.autotag(gallery_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_gallery_autotag", "design_gallery", gallery_id,
                {"enabled": res.get("enabled"), "error": res.get("error", "")})
    return res
