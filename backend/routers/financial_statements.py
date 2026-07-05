"""FINANCE — Laporan Keuangan (Laba-Rugi & Neraca) router.

Akses: permission module "accounting" (admin/manager) — sama seperti GL.
Respons OBJEK telanjang (kontrak KN3). Semua laporan diturunkan dari GL
(`journal_entries`) dan ter-scope per entitas (buku terpisah per PT, F0-E).

Endpoint:
- GET /api/finance/income-statement            → Laba-Rugi (periode)
- GET /api/finance/balance-sheet               → Neraca (posisi, comparative opsional)
- GET /api/finance/income-statement/export.csv → unduh CSV Laba-Rugi
- GET /api/finance/balance-sheet/export.csv     → unduh CSV Neraca
"""
import csv
import io
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, Query, Response

from dependencies import require_permission
from entity_scope import entity_ctx, resolve_list_scope
from services import financial_statement_service as fs

router = APIRouter(prefix="/api")


async def _je_scope(request: Request, entity_id: Optional[str]) -> Dict[str, Any]:
    """Fragmen filter entitas untuk jurnal (default: entitas aktif)."""
    ctx = await entity_ctx(request)
    return resolve_list_scope("journal_entries", {}, ctx, entity_id)


# ═════════════════════════════════════════════════════════════════════════════
#  JSON REPORTS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/finance/income-statement")
async def get_income_statement(
    request: Request,
    start: Optional[str] = Query(None, description="Tanggal awal periode (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="Tanggal akhir periode (YYYY-MM-DD)"),
    entity_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Laba-Rugi (Income Statement) untuk periode — per entitas."""
    await require_permission(request, "accounting", "view")
    scope = await _je_scope(request, entity_id)
    return await fs.income_statement(start=start, end=end, scope=scope)


@router.get("/finance/balance-sheet")
async def get_balance_sheet(
    request: Request,
    as_of: Optional[str] = Query(None, description="Posisi per tanggal (YYYY-MM-DD)"),
    compare_as_of: Optional[str] = Query(None, description="Tanggal pembanding (YYYY-MM-DD) — mode comparative"),
    entity_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Neraca (Balance Sheet) posisi per tanggal — per entitas.

    Bila `compare_as_of` diisi, respons memuat kolom pembanding + delta.
    """
    await require_permission(request, "accounting", "view")
    scope = await _je_scope(request, entity_id)
    return await fs.balance_sheet(as_of=as_of, compare_as_of=compare_as_of, scope=scope)


# ═════════════════════════════════════════════════════════════════════════════
#  CSV EXPORT (Excel-friendly)
# ═════════════════════════════════════════════════════════════════════════════

def _csv_response(rows: List[List[Any]], filename: str) -> Response:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerows(rows)
    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/finance/income-statement/export.csv")
async def export_income_statement(
    request: Request,
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
) -> Response:
    """Unduh Laba-Rugi sebagai CSV (sesuai filter periode)."""
    await require_permission(request, "accounting", "view")
    scope = await _je_scope(request, entity_id)
    data = await fs.income_statement(start=start, end=end, scope=scope)

    rows: List[List[Any]] = [["Laba-Rugi (Income Statement)"]]
    period = data.get("period", {})
    rows.append([f"Periode: {period.get('start') or '-'} s/d {period.get('end') or '-'}"])
    rows.append([])
    rows.append(["Bagian", "Kode", "Nama Akun", "Jumlah"])
    for sec in data.get("sections", []):
        for ln in sec.get("lines", []):
            rows.append([sec["label"], ln["code"], ln["name"], ln["amount"]])
        rows.append([f"Total {sec['label']}", "", "", sec.get("total", 0)])
        rows.append([])
    rows.append(["Laba Kotor", "", "", data.get("gross_profit", 0)])
    rows.append(["Marjin Kotor (%)", "", "", data.get("gross_margin", 0)])
    rows.append(["Laba Bersih", "", "", data.get("net_income", 0)])
    rows.append(["Marjin Bersih (%)", "", "", data.get("net_margin", 0)])
    return _csv_response(rows, "laba-rugi.csv")


@router.get("/finance/balance-sheet/export.csv")
async def export_balance_sheet(
    request: Request,
    as_of: Optional[str] = Query(None),
    compare_as_of: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
) -> Response:
    """Unduh Neraca sebagai CSV (comparative bila `compare_as_of` diisi)."""
    await require_permission(request, "accounting", "view")
    scope = await _je_scope(request, entity_id)
    data = await fs.balance_sheet(as_of=as_of, compare_as_of=compare_as_of, scope=scope)
    comparative = data.get("comparative")

    rows: List[List[Any]] = [["Neraca (Balance Sheet)"]]
    rows.append([f"Posisi per: {data.get('as_of')}"])
    if comparative:
        rows.append([f"Pembanding per: {data.get('compare_as_of')}"])
    rows.append([])

    header = ["Bagian", "Kelompok", "Kode", "Nama Akun", "Jumlah"]
    if comparative:
        header += ["Pembanding", "Delta"]
    rows.append(header)

    def _line_row(bagian: str, kelompok: str, ln: Dict[str, Any]) -> List[Any]:
        base = [bagian, kelompok, ln.get("code", ""), ln.get("name", ""), ln.get("amount", 0)]
        if comparative:
            base += [ln.get("compare_amount", 0), ln.get("delta", 0)]
        return base

    def _total_row(label: str, total: float, compare_total: float = 0.0) -> List[Any]:
        base = [label, "", "", "", total]
        if comparative:
            base += [compare_total, round(total - compare_total, 2)]
        return base

    # Aset
    for sec in data.get("assets", {}).get("sections", []):
        for ln in sec.get("lines", []):
            rows.append(_line_row("Aset", sec["label"], ln))
    rows.append(_total_row("TOTAL ASET", data.get("assets_total", 0),
                           data.get("compare", {}).get("assets_total", 0)))
    rows.append([])

    # Kewajiban
    for sec in data.get("liabilities", {}).get("sections", []):
        for ln in sec.get("lines", []):
            rows.append(_line_row("Kewajiban", sec["label"], ln))
    rows.append(_total_row("TOTAL KEWAJIBAN", data.get("liabilities_total", 0),
                           data.get("compare", {}).get("liabilities_total", 0)))
    rows.append([])

    # Ekuitas
    eq = data.get("equity", {})
    for ln in eq.get("lines", []):
        rows.append(_line_row("Ekuitas", "Modal", ln))
    ce_row = ["Ekuitas", "Laba Tahun Berjalan", "", "", eq.get("current_earnings", 0)]
    if comparative:
        ce_c = eq.get("compare_current_earnings", 0)
        ce_row += [ce_c, round(eq.get("current_earnings", 0) - ce_c, 2)]
    rows.append(ce_row)
    rows.append(_total_row("TOTAL EKUITAS", data.get("equity_total", 0),
                           data.get("compare", {}).get("equity_total", 0)))
    rows.append([])
    rows.append(_total_row("TOTAL KEWAJIBAN + EKUITAS", data.get("liabilities_equity_total", 0),
                           data.get("compare", {}).get("liabilities_equity_total", 0)))
    return _csv_response(rows, "neraca.csv")
