"""Kain Nusantara API — modular FastAPI application."""
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from db import client
import bootstrap

# Import all routers
from routers import (
    auth, users, dashboard, products, customers, warehouses, uoms,
    inventory, sales_orders, invoices, wms, documents, admin,
    reporting, audit, cycle_count, onboarding, label_printer, transfers,
    purchase_orders, inbound_receiving, outbound_picking,
    entities, notifications, settings, price_approvals, pegging, tax_invoices,
    sales_returns, special_orders, approval_rules, approval_requests,
    suppliers, cash, purchase_returns, purchase_requisitions, vendor_bills,
    landed_cost, input_tax, rfq, qc_inspection, crm, home, categories,
    costing, ar_receipts, incentive_rates, ar_aging, bank, gl, pricelist, product_templates,
    stock_buckets, pos, so_approvals, hr, hr_attendance, hr_tracking, hr_payroll,
    hr_leave, hr_kpi, design_gallery, integrations, hr_analytics, tax_center,
    financial_statements, closing, finance_bi, crm_omnichannel, consolidation,
    rfid,
)

# ─── App factory ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await bootstrap.run_bootstrap()
    # Sub-fase 1.7 — init object storage (best-effort; tak menggagalkan startup)
    try:
        from services.storage_service import init_storage
        await init_storage()
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger("server").warning("[storage] init dilewati: %s", exc)
    # FASE H2 — muat cache posisi terkini (live tracking) best-effort
    try:
        from services.tracking_service import hydrate_latest
        await hydrate_latest()
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger("server").warning("[tracking] hydrate dilewati: %s", exc)
    yield
    client.close()


app = FastAPI(title="Kain Nusantara API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
for module in [
    auth, users, dashboard, products, customers, warehouses, uoms,
    inventory, sales_orders, invoices, wms, documents, admin,
    reporting, audit, cycle_count, onboarding, label_printer, transfers,
    purchase_orders, inbound_receiving, outbound_picking,
    entities, notifications, settings, price_approvals, pegging, tax_invoices,
    sales_returns, special_orders, approval_rules, approval_requests,
    suppliers, cash, purchase_returns, purchase_requisitions, vendor_bills,
    landed_cost, input_tax, rfq, qc_inspection, crm, home, categories,
    costing, ar_receipts, incentive_rates, ar_aging, bank, gl, pricelist, product_templates,
    stock_buckets, pos, so_approvals, hr, hr_attendance, hr_tracking, hr_payroll,
    hr_leave, hr_kpi, design_gallery, integrations, hr_analytics, tax_center,
    financial_statements, closing, finance_bi, crm_omnichannel, consolidation,
    rfid,
]:
    app.include_router(module.router)


@app.get("/api/")
async def root():
    return {"message": "Kain Nusantara API aktif"}


# ─── FASE H2 (HRD): Live Field Tracking via WebSocket (wss lewat ingress) ─────
# Manager/admin = subscriber (Live Map); karyawan lapangan = publisher posisi.
# Auth: ?token=<sess_token>  ·  ?mode=subscribe|publish (opsional; default by role).
import json  # noqa: E402
from fastapi import WebSocket, WebSocketDisconnect  # noqa: E402


@app.websocket("/api/ws/track")
async def ws_track(websocket: WebSocket):
    from services.tracking_service import (
        manager as track_manager, auth_ws_token, employee_for_user, store_track,
    )
    token = websocket.query_params.get("token", "")
    mode = websocket.query_params.get("mode", "")
    user = await auth_ws_token(token)
    await websocket.accept()
    if not user:
        await websocket.send_json({"type": "error", "msg": "unauthorized"})
        await websocket.close()
        return

    is_manager = user.get("role") in ("admin", "manager")
    subscribe = (mode == "subscribe") or (mode != "publish" and is_manager)

    if subscribe:
        track_manager.add_subscriber(websocket)
        await websocket.send_json({"type": "snapshot", "data": track_manager.snapshot()})
        try:
            while True:
                await websocket.receive_text()  # keepalive/ping dari klien
        except WebSocketDisconnect:
            track_manager.remove_subscriber(websocket)
        except Exception:  # noqa: BLE001
            track_manager.remove_subscriber(websocket)
        return

    # Publisher (karyawan lapangan) — kirim posisi sendiri
    emp = await employee_for_user(user["id"])
    if not emp:
        await websocket.send_json({"type": "error", "msg": "no-employee-profile"})
        await websocket.close()
        return
    await websocket.send_json({"type": "ready", "msg": "publishing", "employee_id": emp["id"]})
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            if msg.get("type") == "position" and msg.get("lat") is not None and msg.get("lon") is not None:
                pos = await store_track(emp, msg["lat"], msg["lon"],
                                        msg.get("accuracy", 0), msg.get("battery"), source="ws")
                await websocket.send_json({"type": "ack", "ts": pos["ts"]})
    except WebSocketDisconnect:
        return
    except Exception:  # noqa: BLE001
        return
