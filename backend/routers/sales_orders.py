"""Sales orders router: full order lifecycle with reservation engine."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pymongo import ReturnDocument
from db import db
from dependencies import require_permission, audit, current_user
from core_utils import new_id, now_iso, safe_doc, DEFAULT_ENTITY_ID, next_doc_number, strip_cost_fields
from schemas import GenericPatch, SalesOrderCreate, AllocationPreviewIn, RollReconcilePreviewIn
from services.inventory_service import expire_old_reservations
from services.roll_service import (
    allocate_and_reserve_rolls, release_order_rolls, set_order_rolls_status,
    preview_line_allocation, deliver_order_rolls,
    reserve_specific_rolls, allocations_from_reserved_rolls, record_reservation_movements,
    _release_rolls_by_ref_id, compute_roll_reconcile,
)
from services.config_service import compute_order_pricing, evaluate_approval, role_satisfies, get_allocation_policy, get_effective_settings
from services import so_approvals
from services.fulfillment_service import classify_lines
from services.fulfillment_status import recompute_so_status, create_outbound_tasks_for_order
from services.so_status import stage_fields, derive_stage_substatus, SUBSTATUS_LABELS, allowed_action_hint
from routers.price_approvals import get_effective_special_price
from services.uom_service import to_base, load_fixed_factors
from services.customer_service import evaluate_credit_gate, resolve_customer_sales_team
from entity_scope import entity_ctx, resolve_list_scope, stamp_entity
from services import costing_service
from services import pricelist_service
from services.sales_order_helpers import (
    normalize_sales_team as _normalize_sales_team,
    norm_backorder as _norm_backorder,
    reserve_roll_mode_item as _reserve_roll_mode_item,
    so_transition as _transition,
    compute_frequent_products as _compute_frequent_products,
)

router = APIRouter(prefix="/api")


@router.post("/sales-orders/preview-allocation")
async def preview_allocation(payload: AllocationPreviewIn, request: Request) -> Dict[str, Any]:
    """Sub-fase 1.4 — ATP & Fulfillment Modes (READ-ONLY).

    Mengklasifikasikan SUMBER PEMENUHAN per baris (from_stock / from_incoming /
    inter_company / backorder) + ATP per item SEBELUM order dibuat. Dipakai POS
    agar Sales tahu risiko pemenuhan. Tidak memutasi stok / tidak mereservasi.
    """
    await require_permission(request, "order", "view")
    # Resolusi entitas penjual: payload → entitas customer → default.
    entity_id = (payload.entity_id or "").strip()
    if not entity_id and payload.customer_id:
        cust = await db.customers.find_one({"id": payload.customer_id}, {"_id": 0, "entity_id": 1})
        entity_id = (cust or {}).get("entity_id") or DEFAULT_ENTITY_ID
    if not entity_id:
        entity_id = DEFAULT_ENTITY_ID
    # Sub-fase 1.13 — preview pakai base_quantity agar konsisten dengan create_order.
    # S-5 (Gelombang 2) — lookup produk terarah by id (aman utk katalog besar).
    _pids = list({it.product_id for it in payload.items})
    products = {p["id"]: p for p in await db.products.find(
        {"id": {"$in": _pids}}, {"_id": 0}).to_list(len(_pids) + 1)}
    fixed_factors = await load_fixed_factors()
    items = []
    for it in payload.items:
        prod = products.get(it.product_id, {})
        try:
            bq = to_base(prod, float(it.quantity or 0), it.unit, fixed_factors) if prod else float(it.quantity or 0)
        except Exception:  # noqa: BLE001 — preview read-only; jangan gagal keras
            bq = float(it.quantity or 0)
        items.append({"product_id": it.product_id, "quantity": bq, "unit": prod.get("base_unit", "meter")})
    return await classify_lines(items, entity_id)


@router.post("/sales-orders/preview-lots")
async def preview_lots(payload: AllocationPreviewIn, request: Request) -> Dict[str, Any]:
    """Mixed-Lot Confirmation (READ-ONLY) — rencana LOT per baris sebelum order dibuat.

    Menerapkan allocation policy aktif (system→customer). Untuk tiap baris mengembalikan
    lot_mode (single/mixed), lot yang dipakai, qty terpenuhi/backorder, penjelasan, dan
    `requires_confirmation` (true bila kebijakan prefer_single tapi hasil lintas-lot).
    Tidak memutasi stok. Dipakai POS untuk dialog konfirmasi mixed-lot.
    """
    await require_permission(request, "order", "view")
    entity_id = (payload.entity_id or "").strip()
    customer = None
    if payload.customer_id:
        customer = await db.customers.find_one({"id": payload.customer_id}, {"_id": 0})
        if not entity_id:
            entity_id = (customer or {}).get("entity_id") or DEFAULT_ENTITY_ID
    if not entity_id:
        entity_id = DEFAULT_ENTITY_ID
    city = ""
    if customer:
        addrs = customer.get("addresses") or []
        city = (addrs[0].get("city") if addrs else "") or customer.get("city", "")
    policy = await get_allocation_policy(entity_id, customer)
    products = {p["id"]: p for p in await db.products.find({}, {"_id": 0}).to_list(2000)}
    prod_names = {pid: p.get("name", pid) for pid, p in products.items()}
    fixed_factors = await load_fixed_factors()

    lines = []
    requires_any = False
    for it in payload.items:
        prod = products.get(it.product_id, {})
        try:
            bq = to_base(prod, float(it.quantity or 0), it.unit, fixed_factors) if prod else float(it.quantity or 0)
        except Exception:  # noqa: BLE001 — preview read-only
            bq = float(it.quantity or 0)
        plan = await preview_line_allocation(it.product_id, bq, city, entity_id, policy,
                                             customer_id=payload.customer_id)
        plan["product_name"] = prod_names.get(it.product_id, it.product_id)
        requires_any = requires_any or plan["requires_confirmation"]
        lines.append(plan)
    return {
        "entity_id": entity_id,
        "policy": {"lot_mode": policy.get("lot_mode"), "lot_selection": policy.get("lot_selection"),
                   "location_pref": policy.get("location_pref")},
        "requires_confirmation": requires_any,
        "lines": lines,
    }


@router.get("/sales-orders")
async def list_orders(request: Request, status: str = None, customer_id: str = None, entity_id: str = None) -> List[Dict[str, Any]]:
    actor = await require_permission(request, "order", "view")
    await expire_old_reservations()
    ctx = await entity_ctx(request)
    query = {}
    if status:
        query["status"] = status
    if customer_id:
        query["customer_id"] = customer_id
    query = resolve_list_scope("sales_orders", query, ctx, entity_id)
    orders = await db.sales_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    # Defensif: bersihkan ObjectId yang mungkin ter-embed di sub-dokumen (mis. payments[])
    return strip_cost_fields([_norm_backorder(safe_doc(o)) for o in orders], actor.get("role"))


@router.get("/sales-orders/stats/summary")
async def get_orders_stats(request: Request, entity_id: str = None) -> Dict[str, Any]:
    """Get statistics summary for orders monitoring."""
    await require_permission(request, "order", "view")
    await expire_old_reservations()

    # Multi-Entity (RC-7/INV-4): scope identik dgn GET /sales-orders agar
    # total_orders & by_status SELALU konsisten dengan list (tanpa header = entitas
    # AKTIF; X-Entity-Id:all = semua entitas yang diizinkan).
    ctx = await entity_ctx(request)
    scope = resolve_list_scope("sales_orders", {}, ctx, entity_id)

    # Count by status
    pipeline = [
        {"$match": scope},
        {"$group": {"_id": "$status", "count": {"$sum": 1}, "total_amount": {"$sum": "$total_amount"}}}
    ]
    status_counts = {doc["_id"]: {"count": doc["count"], "total_amount": doc["total_amount"]} 
                     for doc in await db.sales_orders.aggregate(pipeline).to_list(100)}
    
    # Reserved qty across all products
    reserved_orders = await db.sales_orders.find(
        {**scope, "status": {"$in": ["reserved", "waiting_approval", "approved"]}},
        {"_id": 0, "allocations": 1, "reservation_expires_at": 1}
    ).to_list(200)
    
    total_reserved_qty = sum(
        alloc.get("quantity", 0) 
        for order in reserved_orders 
        for alloc in order.get("allocations", [])
    )
    
    # Expiring soon (within 24 hours)
    from datetime import datetime, timedelta, timezone
    expiring_soon = sum(
        1 for order in reserved_orders
        if order.get("reservation_expires_at") and 
        datetime.fromisoformat(order["reservation_expires_at"]) < 
        datetime.now(timezone.utc) + timedelta(hours=24)
    )
    
    return {
        "by_status": status_counts,
        "total_reserved_qty": total_reserved_qty,
        "expiring_soon_count": expiring_soon,
        "total_orders": await db.sales_orders.count_documents(scope)
    }


@router.get("/sales-orders/frequent-products")
async def frequent_products(request: Request, customer_id: str = "", limit: int = 8) -> List[Dict[str, Any]]:
    """EPIC5 — "Sering dibeli customer ini" (reorder). Logika di services.sales_order_helpers."""
    actor = await require_permission(request, "order", "view")
    return await _compute_frequent_products(customer_id, limit, actor.get("role"))


@router.post("/sales-orders/preview-roll-reconcile")
async def preview_roll_reconcile(payload: RollReconcilePreviewIn, request: Request) -> List[Dict[str, Any]]:
    """SALES REVAMP V2 (C2) — opsi genapkan roll (round up/down/cut) per baris per-yard."""
    await require_permission(request, "order", "view")
    ctx = await entity_ctx(request)
    selling = (payload.entity_id or getattr(ctx, "active_entity_id", "") or "").strip()
    out: List[Dict[str, Any]] = []
    for it in payload.items:
        target = float(it.base_quantity or it.quantity or 0)
        rec = await compute_roll_reconcile(it.product_id, target, selling, all_entities=bool(payload.all_entities))
        out.append(rec)
    return out


@router.post("/sales-orders")
async def create_order(payload: SalesOrderCreate, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "order", "create")
    # Diskon manual DIHAPUS untuk SEMUA role — potongan harga HANYA via "Ajukan Harga
    # Khusus" (special-price) yang disetujui manager/admin. Payload discount diabaikan.
    customer = safe_doc(await db.customers.find_one({"id": payload.customer_id}, {"_id": 0}))
    if not customer:
        raise HTTPException(status_code=404, detail="Customer tidak ditemukan")
    address = next(
        (a for a in customer.get("addresses", []) if a["id"] == payload.shipping_address_id),
        customer.get("addresses", [{}])[0]
    )
    # S-3 (Gelombang 2) — validasi Order Pengambilan di API (bukan hanya FE):
    # method 'ambil' WAJIB punya pickup_date valid (ISO, tidak di masa lalu).
    fulfillment_method = (getattr(payload, "fulfillment_method", "kirim") or "kirim").strip().lower()
    if fulfillment_method == "ambil":
        pd = (getattr(payload, "pickup_date", "") or "").strip()
        if not pd:
            raise HTTPException(status_code=400,
                                detail="Order Pengambilan membutuhkan tanggal ambil (pickup_date).")
        try:
            pickup_dt = datetime.fromisoformat(pd).date()
        except ValueError:
            raise HTTPException(status_code=400,
                                detail="Format tanggal ambil tidak valid (gunakan YYYY-MM-DD).")
        if pickup_dt < datetime.now(timezone.utc).date():
            raise HTTPException(status_code=400, detail="Tanggal ambil tidak boleh di masa lalu.")
    # S-5 (Gelombang 2) — lookup produk TERARAH by id (bukan cap 100 pertama katalog).
    prod_ids = list({it.product_id for it in payload.items})
    products = {p["id"]: p for p in await db.products.find(
        {"id": {"$in": prod_ids}}, {"_id": 0}).to_list(len(prod_ids) + 1)}
    fixed_factors = await load_fixed_factors()   # Sub-fase 1.13 — peta faktor UOM (FIXED)
    # Resolusi entitas penjual lebih awal (dibutuhkan untuk validasi harga khusus)
    entity_id = payload.entity_id or customer.get("entity_id") or DEFAULT_ENTITY_ID
    # F1a — harga jual per-entitas (pricelist); fallback ke harga global products.price.
    entity_price_map = await pricelist_service.resolve_many(
        entity_id, [it.product_id for it in payload.items], products)
    raw_items = []
    special_count = 0
    for item_in in payload.items:
        product = products.get(item_in.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Produk {item_in.product_id} tidak ditemukan")
        # Sub-fase 1.13 — harga per BASE unit; saat jual di unit lain harga di-skala faktor.
        # (mis. price/meter × (meter per 1 yard) = price/yard) → subtotal konsisten ke base.
        # Faktor dihitung presisi tinggi (precision=6) agar harga tidak kehilangan akurasi;
        # base_quantity (inventori) tetap dibulatkan ke precision 2.
        sell_factor = to_base(product, 1.0, item_in.unit, fixed_factors, precision=6)
        base_sell_price = float((entity_price_map.get(product["id"]) or {}).get("price", product["price"]))
        unit_price = round(base_sell_price * sell_factor, 2)
        special_meta: Dict[str, Any] = {}
        appr_id = (getattr(item_in, "price_approval_id", "") or "").strip()
        if appr_id:
            # Sub-fase 1.7 — harga khusus: harus approved, berlaku, & qty >= min.
            appr = await get_effective_special_price(
                entity_id, customer["id"], product["id"], item_in.quantity, approval_id=appr_id,
            )
            if not appr:
                raise HTTPException(
                    status_code=400,
                    detail=f"Harga khusus untuk {product['name']} tidak berlaku (belum disetujui / kadaluarsa / qty di bawah minimum)",
                )
            unit_price = float(appr["requested_price"])
            special_count += 1
            special_meta = {
                "price_approval_id": appr["id"],
                "special_price": True,
                "normal_price": round(base_sell_price * sell_factor, 2),
            }
        raw_items.append({
            "product_id": product["id"], "sku": product["sku"], "product_name": product["name"],
            "quantity": item_in.quantity, "unit": item_in.unit, "price": unit_price,
            "discount_percent": 0,  # diskon manual dihapus — potongan hanya via Harga Khusus
            **special_meta,
        })
    number = await next_doc_number("sales_orders", "number", "SO-", entity_id=entity_id)
    customer_city = address.get("city", customer.get("city", ""))
    # Fase 1B — pricing engine (diskon item/order + PPN, ikut PKP entitas). INVARIAN-SAFE.
    pricing = await compute_order_pricing(raw_items, entity_id, 0, tax_override=(payload.tax_override or "").strip().lower() or None)
    items = pricing["items"]
    # Sub-fase 1.8 (UOM-safe, forward-compat 1.13): simpan base_unit + base_quantity per item.
    for it in items:
        prod = products.get(it.get("product_id"), {})
        it["base_unit"] = prod.get("base_unit", "meter")
        # Sub-fase 1.13 — base_quantity = qty dikonversi ke base unit (meter).
        it["base_quantity"] = to_base(prod, float(it.get("quantity", 0) or 0), it.get("unit", "meter"), fixed_factors)
        # EPIC2 — snapshot kategori produk ke SO line (basis laporan & insentif per kategori).
        it["category"] = prod.get("category", "")
        # P2-3 — snapshot cost-at-sale (per base unit) agar margin insentif STABIL
        # walau WAC/stok berubah kemudian. Prioritas: WAC saat ini → harga_pokok.
        try:
            w = await costing_service.wac_for_product(it["product_id"], entity_id=entity_id, product=prod)
            cost = float(w.get("wac") or 0)
        except Exception:
            cost = 0.0
        if cost <= 0:
            cost = float(prod.get("harga_pokok") or 0)
        it["unit_cost"] = round(cost, 2)
    total_amount = pricing["total_amount"]            # GROSS = Σ subtotal (invarian)
    # Term pembayaran: pilihan user → fallback default settings
    term_code = (payload.payment_term_code or "").strip()
    if not term_code:
        gs = await db.system_settings.find_one({"scope": "global"}, {"_id": 0}) or {}
        term_code = (gs.get("finance", {}) or {}).get("default_payment_term_code", "NET30")
    term = await db.payment_terms.find_one({"code": term_code}, {"_id": 0})
    # Fase 1B — kebutuhan approval dinamis dari approval_rules (basis grand_total)
    appr = await evaluate_approval("sales_order", pricing["grand_total"], entity_id)
    # KN_17 §5.2 / S37 — Gate kredit. F5 (KEPUTUSAN OWNER §1c): TIDAK lagi blokir 409.
    # Bila over-limit & belum ada override approved → SO TETAP dibuat + dibuat entri
    # pending_approval `kredit` (tombol "Minta Approval Kredit" di detail SO).
    credit_gate = await evaluate_credit_gate(customer, pricing["grand_total"])
    credit_needs_approval = bool(credit_gate["blocked"] and not credit_gate["override"])
    order_id = new_id("so")
    # Sub-fase 1.7 — resolve allocation policy (system→customer→order override)
    alloc_policy = await get_allocation_policy(entity_id, customer)
    # SALES REVAMP V2 — peta item mode "Beli per Roll" (pilihan roll eksplisit) per produk.
    roll_mode_map: Dict[str, List[Dict[str, Any]]] = {}
    for it_in in payload.items:
        if getattr(it_in, "purchase_mode", "qty") == "roll" and getattr(it_in, "roll_lines", None):
            roll_mode_map[it_in.product_id] = [rl.model_dump() for rl in it_in.roll_lines]
    # Mixed-Lot Confirmation gate: bila kebijakan prefer_single tapi hasil lintas-lot,
    # tolak (409 terstruktur) kecuali user sudah konfirmasi (confirm_mixed_lot=true).
    # Item mode 'roll' DILEWATI (user sudah pilih roll/lot eksplisit).
    if not payload.confirm_mixed_lot:
        mixed_items: List[Dict[str, Any]] = []
        for item in items:
            if item["product_id"] in roll_mode_map:
                continue
            prev = await preview_line_allocation(
                item["product_id"], item["base_quantity"], customer_city, entity_id, alloc_policy,
                customer_id=payload.customer_id)
            if prev.get("requires_confirmation"):
                mixed_items.append({
                    "product_id": item["product_id"],
                    "product_name": item.get("product_name") or item.get("name", item["product_id"]),
                    "lots_used": prev.get("lots_used", []),
                    "reserved_qty": prev.get("reserved_qty", 0),
                    "backorder_qty": prev.get("backorder_qty", 0),
                    "explanation": prev.get("explanation", ""),
                })
        if mixed_items:
            raise HTTPException(status_code=409, detail={
                "code": "MIXED_LOT_CONFIRMATION_REQUIRED",
                "message": "Pesanan akan dipenuhi dari beberapa lot berbeda. Konfirmasi diperlukan.",
                "mixed_items": mixed_items,
            })
    # Multi-item reservation di LEVEL ROLL (owner-scoped = entitas penjual; KN_15)
    # Sub-fase 1.6 — bila allow_backorder: reservasi parsial + sisa jadi backorder.
    all_allocations: List[Dict[str, Any]] = []
    backorders: List[Dict[str, Any]] = []
    created_transfer_ids: List[str] = []   # SALES REVAMP V2 — transfer antar-entitas auto (1.b)
    total_pending_ic = 0.0                  # qty menunggu transfer antar-entitas (cross)
    is_split = False
    has_backorder = False
    has_mixed_lot = False
    warehouses_map = {w["id"]: w for w in await db.warehouses.find({}, {"_id": 0}).to_list(200)}
    try:
        for item in items:
            # ── SALES REVAMP V2 — Mode "Beli per Roll" (pilihan roll eksplisit) ──
            if item["product_id"] in roll_mode_map:
                rr = await _reserve_roll_mode_item(
                    order_id, item["product_id"], roll_mode_map[item["product_id"]],
                    entity_id, actor["name"], warehouses_map, products,
                )
                allocs = rr["allocations"]
                created_transfer_ids.extend(rr["transfer_ids"])
                reserved_qty = round(float(rr["reserved_qty"]), 2)
                pending_ic = round(float(rr["pending_qty"]), 2)
                total_pending_ic += pending_ic
                item["reserved_qty"] = reserved_qty
                item["purchase_mode"] = "roll"
                item["roll_lines"] = roll_mode_map[item["product_id"]]
                item["intercompany"] = rr["intercompany"]
                item["intercompany_pending_qty"] = pending_ic
                item["linked_transfer_ids"] = rr["transfer_ids"]
                backorder_qty = round(float(item["base_quantity"]) - reserved_qty - pending_ic, 2)
                if backorder_qty < 0.01:
                    backorder_qty = 0.0
                item["backorder_qty"] = backorder_qty
                if len(allocs) > 1:
                    is_split = True
                item_lots = {l for a in allocs for l in (a.get("lots") or []) if l}
                if len(item_lots) > 1:
                    has_mixed_lot = True
                all_allocations.extend(allocs)
                if backorder_qty > 0.01:
                    has_backorder = True
                    backorders.append({
                        "id": new_id("bo"), "product_id": item["product_id"], "sku": item.get("sku", ""),
                        "product_name": item.get("product_name", ""), "entity_id": entity_id,
                        "customer_city": customer_city, "requested_qty": round(float(item["base_quantity"]), 2),
                        "reserved_qty": reserved_qty, "backorder_qty": backorder_qty,
                        "status": "waiting_stock", "created_at": now_iso(), "updated_at": now_iso(),
                    })
                continue
            # ── Mode "qty" (per yard, FEFO auto) — perilaku lama ──
            allocs = await allocate_and_reserve_rolls(
                item["product_id"], item["base_quantity"], customer_city, entity_id, order_id,
                allow_partial=payload.allow_backorder, policy=alloc_policy, customer_id=payload.customer_id,
            )
            reserved_qty = round(sum(float(a.get("quantity", 0) or 0) for a in allocs), 2)
            backorder_qty = round(float(item["base_quantity"]) - reserved_qty, 2)
            if backorder_qty < 0.01:
                backorder_qty = 0.0
            # Anotasi fulfillment per baris (Sub-fase 1.6)
            item["reserved_qty"] = reserved_qty
            item["backorder_qty"] = backorder_qty
            if len(allocs) > 1:
                is_split = True
            item_lots = {l for a in allocs for l in (a.get("lots") or []) if l}
            if len(item_lots) > 1:
                has_mixed_lot = True
            all_allocations.extend(allocs)
            if backorder_qty > 0.01:
                has_backorder = True
                backorders.append({
                    "id": new_id("bo"),
                    "product_id": item["product_id"],
                    "sku": item.get("sku", ""),
                    "product_name": item.get("product_name", ""),
                    "entity_id": entity_id,
                    "customer_city": customer_city,
                    "requested_qty": round(float(item["base_quantity"]), 2),
                    "reserved_qty": reserved_qty,
                    "backorder_qty": backorder_qty,
                    "status": "waiting_stock",
                    "created_at": now_iso(), "updated_at": now_iso(),
                })
    except HTTPException:
        await release_order_rolls(order_id)
        for _tid in created_transfer_ids:
            await _release_rolls_by_ref_id(_tid)
        if created_transfer_ids:
            await db.warehouse_transfers.delete_many({"id": {"$in": created_transfer_ids}})
        raise
    except Exception as e:
        await release_order_rolls(order_id)
        for _tid in created_transfer_ids:
            await _release_rolls_by_ref_id(_tid)
        if created_transfer_ids:
            await db.warehouse_transfers.delete_many({"id": {"$in": created_transfer_ids}})
        raise HTTPException(status_code=500, detail=str(e))
    expires = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    # Status awal (Sub-fase 1.6.1 — decouple status & backorder):
    #   - reserved      : ada porsi ter-reservasi / menunggu transfer antar-entitas
    #   - waiting_stock : 0 reserved (pure backorder — menunggu stok masuk)
    #   - draft         : tidak ada apa-apa
    total_reserved = round(sum(float(it.get("reserved_qty", 0) or 0) for it in items), 2)
    if total_reserved > 0.01 or total_pending_ic > 0.01:
        initial_status = "reserved"
    elif has_backorder:
        initial_status = "waiting_stock"
    else:
        initial_status = "draft"
    # F5 — Unified Approval SSOT: kumpulkan pending_approvals (nilai + kredit) saat create.
    settings_eff = await get_effective_settings(entity_id)
    require_val = so_approvals.require_validation_default(settings_eff)
    pending_approvals: List[Dict[str, Any]] = []
    if appr["requires_approval"]:
        pending_approvals.append(so_approvals.make_approval(
            "nilai", required_role=appr["required_role"] or "manager",
            reason=f"Nilai order Rp{pricing['grand_total']:,.0f} memerlukan persetujuan.".replace(",", "."),
            requested_by=actor["name"], requested_by_id=actor["id"],
            amount=pricing["grand_total"],
        ))
    credit_override_doc_id = ""
    if credit_needs_approval:
        credit_override_doc_id = new_id("cro")
        pending_approvals.append(so_approvals.make_approval(
            "kredit", required_role="manager",
            reason="; ".join(credit_gate.get("reasons", []) or []) or "Melebihi limit kredit pelanggan.",
            requested_by=actor["name"], requested_by_id=actor["id"], ref_id=credit_override_doc_id,
            amount=pricing["grand_total"],
        ))
    _afields = so_approvals.approval_fields(
        {"pending_approvals": pending_approvals, "required_approval_role": appr["required_role"]},
        require_validation=require_val,
    )
    order = {
        "id": order_id, "number": number, "status": initial_status,
        "entity_id": entity_id,
        "customer_id": customer["id"], "customer_name": customer["name"],
        "customer_city": customer.get("city") or address.get("city"),
        "shipping_address": address, "shipping_address_id": payload.shipping_address_id,
        "shipping_city": address.get("city") or customer.get("city"),
        "items": items, "allocations": all_allocations, "total_amount": total_amount,
        # Fase 1B — breakdown diskon + pajak (field terpisah; invarian total_amount tetap GROSS)
        "items_discount_total": pricing["items_discount_total"],
        "order_discount_percent": pricing["order_discount_percent"],
        "order_discount_amount": pricing["order_discount_amount"],
        "discount_total": pricing["discount_total"],
        "net_subtotal": pricing["net_subtotal"],
        "dpp": pricing["dpp"], "dpp_nilai_lain": pricing.get("dpp_nilai_lain", False),
        "effective_rate": pricing.get("effective_rate", pricing["ppn_rate"]),
        "ppn_rate": pricing["ppn_rate"], "ppn_mode": pricing["ppn_mode"],
        "is_pkp": pricing["is_pkp"], "ppn_amount": pricing["ppn_amount"],
        "grand_total": pricing["grand_total"],
        # F6 — Faktur Pajak per-order + mode pajak efektif (ikut entitas atau override)
        "needs_tax_invoice": bool(getattr(payload, "needs_tax_invoice", False)),
        "tax_override": (getattr(payload, "tax_override", "") or "").strip().lower(),
        "tax_mode": "non_ppn" if not pricing["is_pkp"] else "ppn",
        # Term pembayaran
        "payment_term_code": term_code,
        "payment_term_name": (term or {}).get("name", term_code),
        "payment_status": "pending",
        # KN_17 — snapshot kredit saat order + flag warning + override yang dipakai
        "credit_status_at_order": credit_gate["credit"]["status"],
        "credit_warning": credit_gate["level"] == "warning",
        "credit_hold": credit_needs_approval,
        "credit_override_id": (credit_gate["override"] or {}).get("id", ""),
        # F5 — Unified Approval SSOT (nilai | kredit | special_price)
        "pending_approvals": pending_approvals,
        # Approval (dinamis dari approval_rules + validasi admin wajib)
        "approval_required": _afields["approval_required"],
        "required_approval_role": _afields["required_approval_role"],
        "approval_amount": pricing["grand_total"],
        "is_split_warehouse": is_split, "sales_name": payload.sales_name,
        # SALES REVAMP V2 — tim sales (PIC + co-sales + split) DIWARISI dari customer (bukan order).
        "sales_team": resolve_customer_sales_team(customer),
        # EPIC6 — link eksplisit asal Special Order (bila order dikonversi dari OD).
        "source_special_order_id": (getattr(payload, "source_special_order_id", "") or "").strip() or None,
        "shipment_policy": payload.shipment_policy,
        # Order Pengambilan (pickup) — metode pemenuhan + tanggal ambil (hold picking s/d tgl).
        "fulfillment_method": (getattr(payload, "fulfillment_method", "kirim") or "kirim").strip().lower(),
        "pickup_date": (getattr(payload, "pickup_date", "") or "").strip(),
        "reservation_expires_at": expires,
        # Sub-fase 1.6 — backorder lifecycle
        "allow_backorder": payload.allow_backorder,
        "has_backorder": has_backorder,
        "backorders": backorders,
        # Sub-fase 1.7 — allocation policy snapshot + mixed-lot flag (CLARITY/audit)
        "allocation_policy": {
            "mode": alloc_policy.get("mode"),
            "lot_mode": alloc_policy.get("lot_mode"),
            "lot_selection": alloc_policy.get("lot_selection"),
            "location_pref": alloc_policy.get("location_pref"),
        },
        "has_mixed_lot": has_mixed_lot,
        # SALES REVAMP V2 — transfer antar-entitas auto (Beli per Roll lintas-entitas, 1.b)
        "linked_transfer_ids": created_transfer_ids,
        "intercompany_pending_qty": round(total_pending_ic, 2),
        "created_at": now_iso(), "updated_at": now_iso()
    }
    # F4 — derive stage + sub_status (SSOT 2-level) dari status awal + konteks backorder/approval.
    order.update(stage_fields(order))
    await db.sales_orders.insert_one(order)
    # F5 — buat dokumen detail credit_overrides (pending) yang ditautkan ke entri kredit di SSOT.
    if credit_needs_approval and credit_override_doc_id:
        await db.credit_overrides.insert_one({
            "id": credit_override_doc_id,
            "customer_id": customer["id"], "customer_name": customer["name"],
            "order_id": order_id, "order_number": number,
            "amount": pricing["grand_total"],
            "reason": "; ".join(credit_gate.get("reasons", []) or []) or "Over-limit saat pembuatan SO.",
            "evidence_url": "", "credit_snapshot": credit_gate["credit"],
            "entity_id": entity_id, "status": "pending",
            "requested_by": actor["name"], "requested_by_id": actor["id"],
            "created_at": now_iso(),
        })
    # Konsumsi override kredit bila dipakai untuk melewati blokir (sekali pakai)
    if credit_gate["override"]:
        await db.credit_overrides.update_one(
            {"id": credit_gate["override"]["id"]},
            {"$set": {"consumed": True, "consumed_order_id": order_id, "consumed_at": now_iso()}},
        )
    await audit(actor["name"], "order_created", "sales_order", order["id"], {
        "number": order["number"], "customer": customer["name"], "total_amount": total_amount,
        "grand_total": pricing["grand_total"], "ppn_amount": pricing["ppn_amount"],
        "discount_total": pricing["discount_total"], "payment_term": term_code,
        "approval_required": appr["requires_approval"], "required_role": appr["required_role"],
        "has_backorder": has_backorder,
        "backorder_lines": len(backorders),
        "special_price_lines": special_count,
    })
    return strip_cost_fields(safe_doc(order), actor.get("role"))


@router.get("/sales-orders/{order_id}")
async def get_order(order_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "order", "view")
    order = safe_doc(await db.sales_orders.find_one({"id": order_id}, {"_id": 0}))
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")
    return strip_cost_fields(_norm_backorder(order), actor.get("role"))


@router.patch("/sales-orders/{order_id}")
async def update_order(order_id: str, payload: GenericPatch, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "order", "update")
    allowed = ["sales_name", "shipment_policy", "notes"]
    data = {k: v for k, v in payload.data.items() if k in allowed}
    data["updated_at"] = now_iso()
    order = await db.sales_orders.find_one_and_update(
        {"id": order_id}, {"$set": data},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")
    await audit(actor["name"], "order_updated", "sales_order", order_id, data)
    return strip_cost_fields(order, actor.get("role"))


@router.post("/sales-orders/{order_id}/submit-for-approval")
async def submit_for_approval(order_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "order", "update")
    order = safe_doc(await db.sales_orders.find_one({"id": order_id}, {"_id": 0}))
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")
    # Fase 1B — re-evaluasi kebutuhan approval dari matriks (configurable) basis grand_total
    amount = float(order.get("grand_total", order.get("total_amount", 0)) or 0)
    appr = await evaluate_approval("sales_order", amount, order.get("entity_id"))
    settings_eff = await get_effective_settings(order.get("entity_id"))
    require_val = so_approvals.require_validation_default(settings_eff)
    summ = so_approvals.summarize(order)
    # F5/RBAC — SO WAJIB divalidasi admin/manager (default). Tidak ada auto-approve oleh sales.
    needs = bool(appr["requires_approval"] or summ["has_pending"] or require_val)
    req_role = appr["required_role"] or summ["required_role"] or ("manager" if require_val else "")
    # Pastikan ada entri 'nilai' sebagai penanda validasi bila belum ada approval spesifik.
    pa = list(order.get("pending_approvals") or [])
    if needs and not any(p.get("type") == "nilai" and p.get("status") == "pending" for p in pa) \
            and not any(p.get("type") in ("kredit", "special_price") and p.get("status") == "pending" for p in pa):
        pa.append(so_approvals.make_approval(
            "nilai", required_role=req_role or "manager",
            reason="Validasi admin atas pesanan." if not appr["requires_approval"]
                   else f"Nilai order Rp{amount:,.0f} memerlukan persetujuan.".replace(",", "."),
            requested_by=actor["name"], requested_by_id=actor["id"], amount=amount,
        ))
    await db.sales_orders.update_one({"id": order_id}, {"$set": {
        "pending_approvals": pa,
        "approval_required": needs,
        "required_approval_role": req_role,
        "approval_amount": amount, "updated_at": now_iso(),
    }})
    if needs:
        return strip_cost_fields(
            await _transition(order_id, ["reserved", "waiting_stock"], "waiting_approval", actor["name"],
                              "order_submitted", {"required_approval_role": req_role}),
            actor.get("role"))
    # Validasi nonaktif & di bawah ambang → auto-approve + hard-commit roll
    result = await _transition(order_id, ["reserved"], "approved", actor["name"],
                               "order_auto_approved",
                               {"approval_note": "Auto-approve (validasi nonaktif, di bawah threshold)"})
    await set_order_rolls_status(order_id, "committed")
    return strip_cost_fields(result, actor.get("role"))


async def advance_so_if_all_approved(order_id: str, actor_name: str) -> Optional[Dict[str, Any]]:
    """F5 — SO naik ke Approved HANYA bila SEMUA pending_approvals = approved."""
    order = safe_doc(await db.sales_orders.find_one({"id": order_id}, {"_id": 0}))
    if not order or not so_approvals.all_approved(order):
        return None
    if order.get("status") not in ("reserved", "waiting_approval", "waiting_stock"):
        return None
    result = await _transition(order_id, ["reserved", "waiting_approval", "waiting_stock"], "approved",
                               actor_name, "order_approved", {"approved_by": actor_name})
    await set_order_rolls_status(order_id, "committed")
    return result


@router.post("/sales-orders/{order_id}/approve")
async def approve_order(order_id: str, request: Request) -> Dict[str, Any]:
    # F5/RBAC — APPROVE butuh permission order.approve (sales TIDAK punya → 403).
    actor = await require_permission(request, "order", "approve")
    order = safe_doc(await db.sales_orders.find_one({"id": order_id}, {"_id": 0}))
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")
    required = order.get("required_approval_role")
    if not role_satisfies(actor.get("role"), required):
        raise HTTPException(status_code=403,
            detail=f"Approval butuh role minimal '{required}'. Role Anda: '{actor.get('role')}'.")
    # F5 — blokir bila masih ada approval harga/kredit menunggu (putuskan dulu di Pusat Persetujuan).
    summ = so_approvals.summarize(order)
    blockers = sorted({t for t in summ["pending_types"] if t in ("kredit", "special_price")})
    if blockers:
        names = ", ".join({"kredit": "kredit", "special_price": "harga khusus"}[b] for b in blockers)
        raise HTTPException(status_code=409, detail={
            "code": "APPROVAL_PENDING",
            "message": f"Masih ada persetujuan {names} yang menunggu keputusan. "
                       f"Putuskan dulu di Pusat Persetujuan / detail SO sebelum menyetujui pesanan.",
            "pending_types": summ["pending_types"]})
    pa = list(order.get("pending_approvals") or [])
    for p in pa:
        if p.get("type") == "nilai" and p.get("status") == "pending":
            p.update({"status": "approved", "decided_by": actor["name"],
                      "decided_by_id": actor["id"], "decided_at": now_iso()})
    await db.sales_orders.update_one({"id": order_id}, {"$set": {"pending_approvals": pa, "updated_at": now_iso()}})
    result = await advance_so_if_all_approved(order_id, actor["name"])
    if result is None:
        result = await _transition(order_id, ["reserved", "waiting_approval"], "approved",
                                   actor["name"], "order_approved", {"approved_by": actor["name"]})
        await set_order_rolls_status(order_id, "committed")
    return result


@router.post("/sales-orders/{order_id}/confirm")
async def confirm_order(order_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "order", "confirm")
    result = await _transition(order_id, ["approved", "waiting_approval", "reserved"], "confirmed",
                               actor["name"], "order_confirmed")
    # Sub-fase 1.8 — otomatis buat task outbound saat confirmed (idempotent)
    tasks = await create_outbound_tasks_for_order(order_id, actor["name"])
    if tasks:
        await audit(actor["name"], "outbound_tasks_auto_created", "sales_order", order_id,
                    {"tasks_count": len(tasks)})
    await recompute_so_status(order_id)
    return safe_doc(await db.sales_orders.find_one({"id": order_id}, {"_id": 0}))


@router.post("/sales-orders/{order_id}/mark-delivered")
async def mark_delivered(order_id: str, request: Request) -> Dict[str, Any]:
    """Sub-fase 1.8 — tandai order TERKIRIM/DITERIMA (shipped → done).
    Roll in_transit_sales → 'delivered' (keluar dari owned_qty)."""
    actor = await require_permission(request, "order", "update")
    order = safe_doc(await db.sales_orders.find_one({"id": order_id}, {"_id": 0}))
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")
    if order["status"] != "shipped":
        raise HTTPException(status_code=409,
                            detail=f"Hanya order 'shipped' yang bisa ditandai diterima (saat ini '{order['status']}').")
    delivered = await deliver_order_rolls(order_id)
    result = await _transition(order_id, ["shipped"], "done", actor["name"], "order_delivered",
                               {"delivered_at": now_iso()})
    await audit(actor["name"], "order_delivered", "sales_order", order_id, {"rolls_delivered": delivered})
    return strip_cost_fields(result, actor.get("role"))


@router.post("/sales-orders/{order_id}/release-reservation")
async def release_reservation(order_id: str, request: Request) -> Dict[str, Any]:
    """Manually release reservation without cancelling order (set to draft)."""
    actor = await require_permission(request, "order", "update")
    order = safe_doc(await db.sales_orders.find_one({"id": order_id}, {"_id": 0}))
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")
    if order["status"] not in ["reserved", "waiting_approval", "approved", "waiting_stock"]:
        raise HTTPException(status_code=409, detail="Order tidak dalam status yang di-reserve")
    # Release reservations di level ROLL (KN_15)
    await release_order_rolls(order_id)
    # Update order to draft status
    update_data = {
        "status": "draft", 
        "allocations": [],
        "backorders": [],
        "has_backorder": False,
        "updated_at": now_iso()
    }
    # F4 — sinkronkan stage/sub_status untuk status baru (draft → Reserved/...).
    update_data.update(stage_fields({**order, **update_data}))
    order = await db.sales_orders.find_one_and_update(
        {"id": order_id}, {"$set": update_data},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER
    )
    await audit(actor["name"], "reservation_released", "sales_order", order_id, 
                {"status": "draft", "note": "Reservation released manually"})
    return strip_cost_fields(order, actor.get("role"))


@router.post("/sales-orders/{order_id}/cancel")
async def cancel_order(order_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "order", "update")
    order = safe_doc(await db.sales_orders.find_one({"id": order_id}, {"_id": 0}))
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")
    if order["status"] in ["done", "cancelled", "expired", "partially_shipped", "shipped"]:
        raise HTTPException(status_code=409, detail="Order tidak bisa dibatalkan (sudah terkirim sebagian/penuh atau terminal)")
    if order["status"] in ["reserved", "waiting_approval", "approved", "confirmed", "waiting_stock",
                            "partially_picked", "picked"]:
        await release_order_rolls(order_id)
    result = await _transition(order_id, [order["status"]], "cancelled", actor["name"], "order_cancelled")
    # S-4 (Gelombang 2) — batalkan task picking gudang yang masih aktif utk order ini
    # (antrean gudang bersih; barang order batal tidak ikut disiapkan).
    cancelled_tasks = await db.wms_tasks.update_many(
        {"order_id": order_id, "flow_type": "outbound",
         "status": {"$nin": ["dispatched", "completed", "cancelled"]}},
        {"$set": {"status": "cancelled", "cancel_reason": "SO dibatalkan",
                  "cancelled_by": actor["name"], "updated_at": now_iso()}})
    if cancelled_tasks.modified_count:
        await audit(actor["name"], "outbound_tasks_cancelled", "sales_order", order_id,
                    {"count": cancelled_tasks.modified_count, "reason": "SO dibatalkan"})
    # Gelombang 1 F-1 — jurnal balik otomatis bila order sudah berjurnal (best-effort).
    try:
        from services import gl_service
        await gl_service.reverse_order_journals(order_id, reason="order dibatalkan",
                                                actor_name=actor["name"])
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).error("Gagal reversal GL utk order %s: %s", order_id, exc)
    return strip_cost_fields(result, actor.get("role"))
