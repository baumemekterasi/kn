"""HRD H5 schemas — Design Gallery (motif kain) + AI auto-tag.

Di-re-export via `schemas.py`. Koleksi `design_gallery` (entity-scoped). Upload
gambar via storage lokal (services.storage_service). Lihat memory/PLAN_HRD.md §H5
(keputusan 3a) + §10b HR-Q5 (AI Anthropic Claude langsung, graceful).
"""
from typing import List, Optional
from pydantic import BaseModel


class GalleryInput(BaseModel):
    """Buat entri motif: judul + cerita/deskripsi + tags + (opsional) link produk."""
    title: str = ""
    story: str = ""
    tags: List[str] = []
    product_id: str = ""             # opsional: tautan ke produk (SKU/varian)


class GalleryUpdate(BaseModel):
    """Update parsial entri motif."""
    title: Optional[str] = None
    story: Optional[str] = None
    tags: Optional[List[str]] = None
    product_id: Optional[str] = None
