"""FINANCE — Konsolidasi Grup + Eliminasi Intercompany.

Menghasilkan matriks Per-PT + Eliminasi + Konsolidasi untuk Laba-Rugi (tahun) &
Neraca (as_of). Eliminasi = adjustment level grup (koleksi
`intercompany_eliminations`), TIDAK memodifikasi journal_entries per-PT
(audit trail via dokumen eliminasi). Mendukung eliminasi manual + auto-deteksi
kandidat akun intercompany.

Prinsip keseimbangan: entri eliminasi harus balanced (Σdebit=Σkredit) sehingga
`assets_elim = liabilities_elim + equity_total_elim` dan Neraca konsolidasi tetap
seimbang. equity_total_elim = equity_langsung + net_income_elim.
"""
from typing import Any, Dict, List, Optional

from db import db
from core_utils import new_id, now_iso, safe_doc
from services import financial_statement_service as fs

IC_KEYWORDS = ["intercompany", "inter-co", "interco", "antar entitas",
               "antar-entitas", "antar-pt", "antar pt", "antarperusahaan",
               "antar perusahaan", "ic-", "i/c"]


def _blank() -> Dict[str, float]:
    return {"revenue": 0.0, "cogs": 0.0, "opex": 0.0,
            "assets": 0.0, "liabilities": 0.0, "equity": 0.0}


def _classify_line(acc_type: str, code: str, debit: float, credit: float) -> Dict[str, float]:
    """Kontribusi satu baris jurnal ke metrik (orientasi saldo normal)."""
    d = round(float(debit or 0) - float(credit or 0), 2)  # debit_net
    c = round(float(credit or 0) - float(debit or 0), 2)   # credit_net
    m = _blank()
    if acc_type == "income":
        m["revenue"] += c
    elif acc_type == "expense":
        if code.startswith("5"):
            m["cogs"] += d
        else:
            m["opex"] += d
    elif acc_type == "asset":
        m["assets"] += d
    elif acc_type == "liability":
        m["liabilities"] += c
    elif acc_type == "equity":
        m["equity"] += c
    return m


def _pnl_derive(m: Dict[str, float]) -> Dict[str, float]:
    revenue = round(m.get("revenue", 0), 2)
    cogs = round(m.get("cogs", 0), 2)
    opex = round(m.get("opex", 0), 2)
    expense = round(cogs + opex, 2)
    return {
        "revenue": revenue, "cogs": cogs, "opex": opex, "expense": expense,
        "gross_profit": round(revenue - cogs, 2),
        "net_income": round(revenue - expense, 2),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  PER-PT & SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

async def _entity_row(eid: str, ent: Dict[str, Any], year: int, as_of: str) -> Dict[str, Any]:
    scope = {"entity_id": eid}
    pnl = await fs.income_statement(start=f"{year}-01-01", end=f"{year}-12-31", scope=scope)
    bs = await fs.balance_sheet(as_of=as_of, scope=scope)
    revenue = float(pnl.get("revenue_total", 0) or 0)
    cogs = float(pnl.get("cogs_total", 0) or 0)
    opex = float(pnl.get("opex_total", 0) or 0)
    return {
        "entity_id": eid,
        "entity_name": ent.get("legal_name") or ent.get("short_name") or eid,
        "short_name": ent.get("short_name") or ent.get("doc_prefix") or eid,
        "revenue": round(revenue, 2),
        "cogs": round(cogs, 2),
        "opex": round(opex, 2),
        "expense": round(cogs + opex, 2),
        "gross_profit": round(revenue - cogs, 2),
        "net_income": float(pnl.get("net_income", 0) or 0),
        "assets": float(bs.get("assets_total", 0) or 0),
        "liabilities": float(bs.get("liabilities_total", 0) or 0),
        "equity": float(bs.get("equity_total", 0) or 0),
    }


async def _applicable_eliminations(year: int, as_of: str):
    """Kembalikan (pl_elims, bs_elims) sesuai filter tanggal efektif."""
    all_elims = await db.intercompany_eliminations.find({}, {"_id": 0}).to_list(2000)
    y0, y1 = f"{year}-01-01", f"{year}-12-31"
    pl = [e for e in all_elims if y0 <= (e.get("effective_date") or "")[:10] <= y1]
    bs = [e for e in all_elims if (e.get("effective_date") or "")[:10] <= as_of]
    return pl, bs, all_elims


def _aggregate_impacts(elims: List[Dict[str, Any]]) -> Dict[str, float]:
    total = _blank()
    for e in elims:
        imp = e.get("impact") or _blank()
        for k in total:
            total[k] += float(imp.get(k, 0) or 0)
    return {k: round(v, 2) for k, v in total.items()}


async def summary(entity_ids: List[str], year: int, as_of: str) -> Dict[str, Any]:
    # M-3: Sinkronisasi otomatis eliminasi dari intercompany_pair_id (idempotent).
    # Setiap kali laporan konsolidasi dibuka, pair baru yang belum ter-cover akan
    # otomatis mendapat entri eliminasi. Hasilnya masuk ke `intercompany_eliminations`.
    try:
        await sync_ic_eliminations_from_pairs(as_of=as_of)
    except Exception:
        # Jangan gagalkan konsolidasi hanya karena sync gagal (mis. race). Log ringan.
        pass

    ents = {e["id"]: e for e in await db.business_entities.find(
        {"id": {"$in": list(entity_ids)}}, {"_id": 0}).to_list(200)}

    rows: List[Dict[str, Any]] = []
    for eid in entity_ids:
        e = ents.get(eid, {})
        if e.get("is_group"):
            continue
        rows.append(await _entity_row(eid, e, year, as_of))
    rows.sort(key=lambda r: r["revenue"], reverse=True)

    sum_fields = ["revenue", "cogs", "opex", "expense", "gross_profit",
                  "net_income", "assets", "liabilities", "equity"]
    gross = {f: round(sum(float(r.get(f, 0) or 0) for r in rows), 2) for f in sum_fields}

    pl_elims, bs_elims, _all = await _applicable_eliminations(year, as_of)
    pl_agg = _aggregate_impacts(pl_elims)
    bs_agg = _aggregate_impacts(bs_elims)
    pl_elim = _pnl_derive(pl_agg)
    # net income effect (dari baris P&L pada eliminasi BS) → mempengaruhi ekuitas
    bs_ni = _pnl_derive(bs_agg)["net_income"]
    equity_total_elim = round(bs_agg.get("equity", 0) + bs_ni, 2)
    elimination = {
        "revenue": pl_elim["revenue"], "cogs": pl_elim["cogs"], "opex": pl_elim["opex"],
        "expense": pl_elim["expense"], "gross_profit": pl_elim["gross_profit"],
        "net_income": pl_elim["net_income"],
        "assets": round(bs_agg.get("assets", 0), 2),
        "liabilities": round(bs_agg.get("liabilities", 0), 2),
        "equity": equity_total_elim,
    }

    consolidated = {
        "revenue": round(gross["revenue"] + elimination["revenue"], 2),
        "cogs": round(gross["cogs"] + elimination["cogs"], 2),
        "opex": round(gross["opex"] + elimination["opex"], 2),
        "assets": round(gross["assets"] + elimination["assets"], 2),
        "liabilities": round(gross["liabilities"] + elimination["liabilities"], 2),
        "equity": round(gross["equity"] + elimination["equity"], 2),
    }
    consolidated["expense"] = round(consolidated["cogs"] + consolidated["opex"], 2)
    consolidated["gross_profit"] = round(consolidated["revenue"] - consolidated["cogs"], 2)
    consolidated["net_income"] = round(consolidated["revenue"] - consolidated["expense"], 2)

    balanced = abs(consolidated["assets"] - (consolidated["liabilities"] + consolidated["equity"])) < 1.0

    return {
        "year": year,
        "as_of": as_of,
        "entities": rows,
        "gross": gross,
        "elimination": elimination,
        "consolidated": consolidated,
        "eliminations_count": len(_all),
        "eliminations_pl_count": len(pl_elims),
        "eliminations_bs_count": len(bs_elims),
        "eliminations_auto_count": sum(1 for e in _all if e.get("auto_generated")),
        "balanced": balanced,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  ELIMINATIONS CRUD
# ═══════════════════════════════════════════════════════════════════════════

async def _accounts_lookup() -> Dict[str, Dict[str, Any]]:
    accs = await db.gl_accounts.find({}, {"_id": 0, "code": 1, "name": 1, "type": 1}).to_list(2000)
    return {a["code"]: a for a in accs}


async def _compute_impact(lines: List[Dict[str, Any]], amap: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    total = _blank()
    for ln in lines:
        acc = amap.get(ln.get("account_code"), {})
        contrib = _classify_line(acc.get("type", ""), ln.get("account_code", ""),
                                 ln.get("debit", 0), ln.get("credit", 0))
        for k in total:
            total[k] += contrib[k]
    return {k: round(v, 2) for k, v in total.items()}


async def list_eliminations() -> List[Dict[str, Any]]:
    return await db.intercompany_eliminations.find({}, {"_id": 0}).sort("effective_date", -1).to_list(1000)


async def create_elimination(data: Dict[str, Any], actor: Dict[str, Any]) -> Dict[str, Any]:
    amap = await _accounts_lookup()
    raw_lines = data.get("lines") or []
    lines: List[Dict[str, Any]] = []
    total_d = total_c = 0.0
    for ln in raw_lines:
        code = (ln.get("account_code") or "").strip()
        if not code:
            continue
        debit = round(float(ln.get("debit") or 0), 2)
        credit = round(float(ln.get("credit") or 0), 2)
        if abs(debit) < 0.005 and abs(credit) < 0.005:
            continue
        lines.append({
            "account_code": code,
            "account_name": amap.get(code, {}).get("name", code),
            "debit": debit, "credit": credit,
            "description": (ln.get("description") or "").strip(),
        })
        total_d += debit
        total_c += credit
    if not lines:
        raise ValueError("Minimal satu baris eliminasi diperlukan.")
    balanced = abs(round(total_d - total_c, 2)) < 0.5
    impact = await _compute_impact(lines, amap)
    doc = {
        "id": new_id("icelim"),
        "name": (data.get("name") or "Eliminasi Intercompany").strip(),
        "entity_from": data.get("entity_from") or None,
        "entity_to": data.get("entity_to") or None,
        "effective_date": (data.get("effective_date") or now_iso())[:10],
        "note": (data.get("note") or "").strip(),
        "lines": lines,
        "total_debit": round(total_d, 2),
        "total_credit": round(total_c, 2),
        "balanced": balanced,
        "impact": impact,
        "created_by": actor.get("name", "system"),
        "created_by_id": actor.get("id"),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.intercompany_eliminations.insert_one(dict(doc))
    return safe_doc(doc)


async def delete_elimination(elim_id: str) -> bool:
    r = await db.intercompany_eliminations.delete_one({"id": elim_id})
    return r.deleted_count > 0


# ═══════════════════════════════════════════════════════════════════════════
#  AUTO-ELIMINATION FROM INTERCOMPANY_PAIR_ID (M-3)
# ═══════════════════════════════════════════════════════════════════════════
# Setiap inter-company transfer meng-post 2 JE (source & dest) yang dilink via
# `intercompany_pair_id`. Konsolidasi grup harus meng-eliminasi:
#   Cr 1-1250 IC-AR (source side) DAN Dr 2-1250 IC-AP (dest side)
# supaya piutang↔utang antar-PT tidak double-counted di neraca konsolidasi.
# Fungsi di bawah menghasilkan/memelihara entri `intercompany_eliminations`
# secara idempotent berdasarkan pair_id. User boleh delete manual bila perlu.

async def _pair_totals(as_of: str = "") -> List[Dict[str, Any]]:
    """Agregat total nilai per intercompany_pair_id dari journal_entries (posted).

    Return list of {pair_id, total, source_entity_id, dest_entity_id,
    effective_date, source_je_ids, dest_je_ids}.
    """
    q: Dict[str, Any] = {
        "intercompany_pair_id": {"$exists": True, "$ne": None},
        "status": {"$ne": "void"},
    }
    if as_of:
        q["date"] = {"$lte": f"{as_of}T23:59:59+00:00"}
    entries = await db.journal_entries.find(q, {"_id": 0}).to_list(20000)
    pairs: Dict[str, Dict[str, Any]] = {}
    for e in entries:
        pid = e.get("intercompany_pair_id")
        if not pid:
            continue
        p = pairs.setdefault(pid, {
            "pair_id": pid, "total": 0.0,
            "source_entity_id": None, "dest_entity_id": None,
            "effective_date": e.get("date", "")[:10],
            "source_je_ids": [], "dest_je_ids": [],
        })
        stype_id = str(e.get("source_id") or "")
        is_src = stype_id.endswith(":src")
        is_dst = stype_id.endswith(":dst")
        if is_src:
            p["source_entity_id"] = e.get("entity_id")
            p["source_je_ids"].append(e.get("id"))
            p["total"] = max(p["total"], float(e.get("total_debit", 0) or 0))
        elif is_dst:
            p["dest_entity_id"] = e.get("entity_id")
            p["dest_je_ids"].append(e.get("id"))
        # tanggal paling awal jadi effective_date
        edate = (e.get("date") or "")[:10]
        if edate and (not p["effective_date"] or edate < p["effective_date"]):
            p["effective_date"] = edate
    return [p for p in pairs.values()
            if p["source_entity_id"] and p["dest_entity_id"] and p["total"] > 0]


async def sync_ic_eliminations_from_pairs(as_of: str = "") -> Dict[str, Any]:
    """Idempotent: buat entri eliminasi otomatis untuk setiap intercompany_pair_id
    yang belum tercatat di `intercompany_eliminations`.

    Logika eliminasi (nol-kan piutang↔utang antar-PT di neraca konsolidasi):
      Dr 2-1250 IC-AP  <total>   (offset saldo IC-AP di dest)
      Cr 1-1250 IC-AR  <total>   (offset saldo IC-AR di source)
    Impact: assets -total, liabilities -total → equity tidak berubah, neraca tetap
    seimbang di level grup.
    """
    from services.gl_service import ACC_IC_AR, ACC_IC_AP
    pairs = await _pair_totals(as_of=as_of)
    amap = await _accounts_lookup()

    existing = await db.intercompany_eliminations.find(
        {"source_pair_id": {"$exists": True, "$ne": None}},
        {"_id": 0, "source_pair_id": 1}).to_list(5000)
    covered = {e["source_pair_id"] for e in existing}

    created: List[Dict[str, Any]] = []
    skipped = 0
    for p in pairs:
        if p["pair_id"] in covered:
            skipped += 1
            continue
        total = round(float(p["total"]), 2)
        lines = [
            {"account_code": ACC_IC_AP, "account_name": amap.get(ACC_IC_AP, {}).get("name", ACC_IC_AP),
             "debit": total, "credit": 0.0,
             "description": f"Eliminasi IC-AP (pair {p['pair_id']})"},
            {"account_code": ACC_IC_AR, "account_name": amap.get(ACC_IC_AR, {}).get("name", ACC_IC_AR),
             "debit": 0.0, "credit": total,
             "description": f"Eliminasi IC-AR (pair {p['pair_id']})"},
        ]
        impact = await _compute_impact(lines, amap)
        doc = {
            "id": new_id("icelim"),
            "name": f"Auto: Eliminasi IC transfer {p['pair_id']}",
            "entity_from": p["source_entity_id"],
            "entity_to": p["dest_entity_id"],
            "effective_date": p["effective_date"] or now_iso()[:10],
            "note": "Auto-generated dari intercompany transfer JE pair. "
                    "Menghapus dobel-hitung piutang↔utang antar-PT di neraca konsolidasi.",
            "lines": lines,
            "total_debit": total,
            "total_credit": total,
            "balanced": True,
            "impact": impact,
            "auto_generated": True,
            "source_pair_id": p["pair_id"],
            "source_je_ids": p["source_je_ids"] + p["dest_je_ids"],
            "created_by": "system",
            "created_by_id": None,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        await db.intercompany_eliminations.insert_one(dict(doc))
        created.append(safe_doc(doc))
    return {
        "created": len(created), "skipped_existing": skipped,
        "pairs_seen": len(pairs), "entries": created,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  AUTO-DETECT INTERCOMPANY CANDIDATES
# ═══════════════════════════════════════════════════════════════════════════

def _is_ic_account(acc: Dict[str, Any]) -> bool:
    hay = f"{acc.get('code','')} {acc.get('name','')}".lower()
    return any(kw in hay for kw in IC_KEYWORDS)


async def ic_candidates(entity_ids: List[str], as_of: str) -> Dict[str, Any]:
    amap = await _accounts_lookup()
    ic_accounts = {code: a for code, a in amap.items() if _is_ic_account(a)}
    ents = {e["id"]: e for e in await db.business_entities.find(
        {"id": {"$in": list(entity_ids)}}, {"_id": 0}).to_list(200)}

    # agregat saldo per entitas per akun IC
    date_filter = {"$lte": fs._day_end(as_of)} if as_of else None
    candidates: List[Dict[str, Any]] = []
    suggested_lines: List[Dict[str, Any]] = []

    per_account: Dict[str, Dict[str, float]] = {code: {} for code in ic_accounts}
    for eid in entity_ids:
        e = ents.get(eid, {})
        if e.get("is_group"):
            continue
        agg = await fs._aggregate({"entity_id": eid}, date_filter, include_closing=True)
        for code in ic_accounts:
            v = agg.get(code)
            if not v:
                continue
            net = round(v["debit"] - v["credit"], 2)  # debit_net
            if abs(net) > 0.005:
                per_account[code][eid] = net

    for code, acc in ic_accounts.items():
        by_ent = per_account.get(code, {})
        if not by_ent:
            continue
        total_net = round(sum(by_ent.values()), 2)
        per_entity = [{
            "entity_id": eid,
            "short_name": (ents.get(eid, {}) or {}).get("short_name", eid),
            "balance": bal,
        } for eid, bal in by_ent.items()]
        candidates.append({
            "account_code": code,
            "account_name": acc.get("name", code),
            "type": acc.get("type", ""),
            "per_entity": per_entity,
            "total_net": total_net,
        })
        # saran baris eliminasi: balikkan saldo total (debit_net>0 → kredit; sebaliknya)
        if abs(total_net) > 0.005:
            if total_net > 0:
                suggested_lines.append({"account_code": code, "account_name": acc.get("name", code),
                                        "debit": 0.0, "credit": abs(total_net),
                                        "description": f"Eliminasi {acc.get('name', code)}"})
            else:
                suggested_lines.append({"account_code": code, "account_name": acc.get("name", code),
                                        "debit": abs(total_net), "credit": 0.0,
                                        "description": f"Eliminasi {acc.get('name', code)}"})

    return {
        "as_of": as_of,
        "keywords": IC_KEYWORDS,
        "candidates": candidates,
        "suggested_lines": suggested_lines,
        "detected_accounts": len(ic_accounts),
    }
