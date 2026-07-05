"""HRD H5 services — Design Gallery (motif kain) + upload gambar (storage lokal).

Koleksi kanonik (entity-scoped): `design_gallery` (dsgn_). Keputusan owner 3a:
upload gambar (JPG/PNG ≤10MB via storage_service) + judul + cerita + tags +
(opsional) link produk. AI auto-tag GRACEFUL via hr_ai_service (HR-Q5).

CATATAN storage: `storage_service.get_object()` MENGEMBALIKAN TUPLE (data, ctype).
"""
from typing import Any, Dict, List, Optional

from db import db
from core_utils import new_id, now_iso, safe_doc
from services import storage_service as storage
from services import hr_ai_service


def _clean_tags(tags) -> List[str]:
    out, seen = [], set()
    for t in (tags or []):
        s = str(t).strip()
        k = s.lower()
        if s and k not in seen:
            seen.add(k)
            out.append(s)
    return out[:30]


async def create_gallery(payload: Dict[str, Any], actor_name: str, entity_id: str) -> Dict[str, Any]:
    title = (payload.get("title") or "").strip()
    if not title:
        raise ValueError("Judul motif wajib diisi.")
    doc = {
        "id": new_id("dsgn"),
        "title": title, "story": payload.get("story", ""),
        "tags": _clean_tags(payload.get("tags")),
        "files": [], "product_id": payload.get("product_id", ""),
        "ai_meta": {"enabled": False, "model": "", "tags": [], "summary": "",
                    "attributes": {}, "analyzed_at": ""},
        "entity_id": entity_id,
        "created_by": actor_name, "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.design_gallery.insert_one(doc)
    return safe_doc(doc)


async def list_gallery(scope: Dict[str, Any], tag: Optional[str] = None,
                       q: Optional[str] = None) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = dict(scope or {})
    if tag:
        query["tags"] = tag
    rows = await db.design_gallery.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)
    rows = [safe_doc(r) for r in rows]
    if q:
        s = q.lower()
        rows = [r for r in rows if s in (r.get("title", "") or "").lower()
                or s in (r.get("story", "") or "").lower()
                or any(s in (t or "").lower() for t in (r.get("tags") or []))]
    return rows


async def get_gallery(gallery_id: str) -> Optional[Dict[str, Any]]:
    return safe_doc(await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0}))


async def update_gallery(gallery_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    from pymongo import ReturnDocument
    cur = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not cur:
        raise ValueError("Entri galeri tidak ditemukan.")
    updates: Dict[str, Any] = {}
    if patch.get("title") is not None:
        if not str(patch["title"]).strip():
            raise ValueError("Judul motif tidak boleh kosong.")
        updates["title"] = str(patch["title"]).strip()
    if patch.get("story") is not None:
        updates["story"] = patch["story"]
    if patch.get("product_id") is not None:
        updates["product_id"] = patch["product_id"]
    if patch.get("tags") is not None:
        updates["tags"] = _clean_tags(patch["tags"])
    if not updates:
        raise ValueError("Tidak ada field valid untuk diupdate.")
    updates["updated_at"] = now_iso()
    doc = await db.design_gallery.find_one_and_update(
        {"id": gallery_id}, {"$set": updates},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    return safe_doc(doc)


async def delete_gallery(gallery_id: str) -> Dict[str, Any]:
    cur = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not cur:
        raise ValueError("Entri galeri tidak ditemukan.")
    await db.design_gallery.delete_one({"id": gallery_id})
    return {"id": gallery_id, "deleted": True}


async def add_file(gallery_id: str, filename: str, content_type: str, data: bytes) -> Dict[str, Any]:
    cur = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not cur:
        raise ValueError("Entri galeri tidak ditemukan.")
    ct = storage.validate_upload(filename, content_type, len(data))  # raise ValueError bila invalid
    ext = storage.ext_of(filename)
    path = storage.build_path("design_gallery", ext)
    await storage.put_object(path, data, ct)
    fmeta = {
        "id": new_id("file"), "filename": filename, "path": path,
        "content_type": ct, "size": len(data), "uploaded_at": now_iso(),
    }
    await db.design_gallery.update_one(
        {"id": gallery_id},
        {"$push": {"files": fmeta}, "$set": {"updated_at": now_iso()}})
    return safe_doc(fmeta)


def _find_file(doc: Dict[str, Any], file_id: str) -> Optional[Dict[str, Any]]:
    for f in (doc.get("files") or []):
        if f.get("id") == file_id:
            return f
    return None


async def get_file_bytes(gallery_id: str, file_id: str):
    """Return (data, content_type) untuk file dalam galeri. Raise ValueError bila tak ada."""
    doc = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not doc:
        raise ValueError("Entri galeri tidak ditemukan.")
    fmeta = _find_file(doc, file_id)
    if not fmeta:
        raise ValueError("File tidak ditemukan.")
    data, ctype = await storage.get_object(fmeta["path"])  # storage MENGEMBALIKAN TUPLE
    return data, fmeta.get("content_type") or ctype


async def delete_file(gallery_id: str, file_id: str) -> Dict[str, Any]:
    doc = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not doc:
        raise ValueError("Entri galeri tidak ditemukan.")
    if not _find_file(doc, file_id):
        raise ValueError("File tidak ditemukan.")
    await db.design_gallery.update_one(
        {"id": gallery_id},
        {"$pull": {"files": {"id": file_id}}, "$set": {"updated_at": now_iso()}})
    return {"id": file_id, "deleted": True}


async def autotag(gallery_id: str) -> Dict[str, Any]:
    """Auto-tag motif via AI (Claude). GRACEFUL: bila AI nonaktif → {enabled:False}.
    Bila sukses → simpan ai_meta + gabung tag unik ke tags[]. Return ai_meta-like."""
    doc = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not doc:
        raise ValueError("Entri galeri tidak ditemukan.")
    files = doc.get("files") or []
    if not files:
        return {"enabled": await hr_ai_service.is_enabled(), "error": "Belum ada gambar untuk dianalisa."}
    fmeta = files[0]
    data, ctype = await storage.get_object(fmeta["path"])
    result = await hr_ai_service.autotag_image(
        data, fmeta.get("content_type") or ctype, context=f"Judul: {doc.get('title', '')}.")
    # Persist ai_meta selalu (transparansi status), gabung tags bila sukses.
    ai_meta = {
        "enabled": bool(result.get("enabled")),
        "model": result.get("model", ""),
        "tags": result.get("tags", []),
        "summary": result.get("summary", ""),
        "attributes": result.get("attributes", {}),
        "analyzed_at": result.get("analyzed_at", now_iso()),
        "error": result.get("error", ""),
    }
    set_doc: Dict[str, Any] = {"ai_meta": ai_meta, "updated_at": now_iso()}
    if result.get("enabled") and result.get("tags") and not result.get("error"):
        merged = _clean_tags(list(doc.get("tags") or []) + list(result.get("tags") or [])) 
        set_doc["tags"] = merged
    await db.design_gallery.update_one({"id": gallery_id}, {"$set": set_doc})
    updated = safe_doc(await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0}))
    return {**result, "gallery": updated}
