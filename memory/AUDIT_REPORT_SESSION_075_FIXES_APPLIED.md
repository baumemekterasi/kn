# AUDIT REPORT — SESSION #075 · Perbaikan Diterapkan (Remediation Applied)

> Kelanjutan dari **#074** (`AUDIT_REPORT_SESSION_074_REMEDIATION.md`). Sesi ini
> **menerapkan perbaikan** untuk temuan #074 lalu **memverifikasi ulang secara empiris**
> (skrip forensik + gate + testing-agent independen). Untuk detail root-cause tiap bug, lihat #074;
> di sini hanya status fix, file yang disentuh, bukti before→after, cara verifikasi, dan sisa follow-up.

- **Tanggal:** 2026-07-05
- **Verifikasi independen:** testing-agent → **28/28 backend PASS (100%)**, 0 bug kritis, 0 regresi (`/app/test_reports/iteration_114.json`).
- **Gate akhir:** `python scripts/verify_data_integrity.py` → **PASS 123 · FAIL 0 · WARN 1** (WARN = COGS-ZERO, follow-up).
- **File aplikasi yang diubah (15):** `routers/{admin,invoices,landed_cost,onboarding,qc_inspection,sales_orders,sales_returns,special_orders,uoms,vendor_bills,wms}.py`, `schemas.py`, `services/{gl_service,purchase_return_service,return_service}.py`.
- **Tooling diubah (2):** `scripts/verify_data_integrity.py` (gate diperkuat), `seed_realistic.py` (true-up saldo awal).
- **Frontend/src:** tidak diubah.

---

## Status per temuan

| Sev | ID | Status | Bukti verifikasi (sesi ini) |
|---|---|---|---|
| 🔴P0 | **RET-2** | ✅ FIXED | approve → `credit_note_id` terisi, `credit_notes +1`, JE `sales_return` +1 **seimbang (327450=327450)** |
| 🔴P0 | **PRET-GL** | ✅ FIXED | approve retur beli → `pret_JE 0→1`, Persediaan Δ=−370000 (Dr GR/IR karena PO belum ditagih) |
| 🔴P0 | **VB-CANCEL-GL** | ✅ FIXED | cancel bill posted → reversal JE +1, **AP −24.75jt→0**, GR/IR→0 |
| 🔴P0 | **IDOR-WRITE** | ✅ FIXED | matriks 2-arah **LEAK=0** kedua arah; **regresi same-entity OK** (sales ent_ksc tetap bisa GET/PATCH order ent_ksc) |
| 🟠P1 | **LC-APPLY-GL** | ✅ FIXED | approve LC → GL 1-1300 Δ=+5.000.000 = alokasi, JE `landed_cost` +1 |
| 🟠P1 | **META-GATE-GL** | ✅ FIXED | inject JE debit1000≠kredit1 → gate **FAIL** (dulu lolos). +cek trial-balance & rekonsiliasi |
| 🟡P2 | **RET-500** | ✅ FIXED | approve/reject id ngawur → **404** (sweep: 180 rute, **0 crash**) |
| 🟡P2 | **LC-PAY** | ✅ FIXED | bayar LC → JE **Dr Hutang / Cr Kas** (bukan Beban Angkut) + inline (tak tergantung backfill) |
| 🟡P2 | **IMP-NONUTF8-500** | ✅ FIXED | file non-UTF8 → **400** |
| 🟡P2 | **IMP-CSV-INJECTION** | ✅ FIXED | export meng-escape → `AUDITINJ9,'=cmd\|x` (apostrof, inert di Excel) |
| 🟡P2 | **IMP-NEG-PRICE / INF** | ✅ FIXED | harga −5000 / `inf` → ditolak (`errors`, created=0) |
| 🟡P2 | **VAL-UOM** | ✅ FIXED | `factor_to_base` ≤0 → **422**; >0 → 200 |
| 🔵P3 | **IMP-IMG-XSS** | ✅ FIXED | `javascript:` image → ditolak (whitelist http/https) |
| 🔵P3 | **ONBOARD-NOOP** | ✅ FIXED | task ngawur → **404**; task valid → 200 |
| 🔵P3 | **RET-ATT-NOOP** | ✅ FIXED | delete attachment id ngawur → **404** |
| 🔵P3 | **INV-GL-DRIFT** | ✅ FIXED | seed true-up saldo awal → gate **rekonsiliasi persediaan PASS** (dulu Δ 532jt) |
| 🟡P2 | **COGS-ZERO** | ⏳ FOLLOW-UP (gated WARN) | Kini **terdeteksi gate (WARN)**. Fix penuh butuh data cost mengalir ke fulfillment (risiko regresi) — sengaja tidak dipaksakan |
| — | **IMP-XENT-CLOBBER** | ℹ️ BY-DESIGN | `products` = SHARED master-data; overwrite SKU memang lintas-entitas by-design (bukan bug) |
| 🔵P3 | **FE-A11Y-DIALOG** | ⏳ FOLLOW-UP (kosmetik) | Warning `DialogTitle` Radix; non-fungsional, tidak diubah agar tak menyentuh frontend |
| 🔵P3 | **AUTH-ORDER** | ℹ️ WONTFIX | Perilaku inheren FastAPI (422 sebelum 401); bukan bug |

---

## Ringkasan teknis perubahan

1. **Gate diperkuat** (`scripts/verify_data_integrity.py`, `layer_gl_invariants`): GL-1 setiap JE seimbang *(FAIL)*, GL-2 trial-balance per entitas *(FAIL)*, GL-3 rekonsiliasi persediaan *(WARN)*, GL-4 deteksi COGS-ZERO *(WARN)*.
2. **RET-2** (`services/gl_service.py` + `services/return_service.py`): tambah `gl_service._avg_unit_cost` (helper yang hilang), dan ubah `except: pass` menjadi log agar kegagalan GL tidak senyap lagi.
3. **RET-500 + sales-return IDOR + RET-ATT-NOOP** (`routers/sales_returns.py`): `approve`/`reject`/`submit`/`delete_attachment` kini fetch dokumen → 404 → `assert_entity_access` sebelum aksi; `delete_attachment` cek keberadaan lampiran.
4. **GL family** (`services/gl_service.py`): tambah `reverse_vendor_bill`, `post_purchase_return`, `post_landed_cost` (idempotent, seimbang). Di-wire: `routers/vendor_bills.py` (cancel posted → reversal), `services/purchase_return_service.py` (approve → posting), `routers/landed_cost.py` (approve → posting; pay → GL inline Dr Hutang/Cr Kas). Mapping kas `ref_type=landed_cost` diubah `5-9000`→`2-1100` (hindari double-count).
5. **IDOR-WRITE** (`routers/{sales_orders,invoices,wms,qc_inspection,special_orders}.py`): `assert_entity_access` pada endpoint tulis (get/update/submit/approve/mark-delivered/release-reservation/cancel SO, simulate-payment, wms scan/advance, roll inspect, patch special-order).
6. **Import hardening** (`routers/admin.py`): decode UTF-8 → 400 bila gagal; `openpyxl` di-guard + `data_only`; validasi harga ≥0 & berhingga; whitelist skema URL gambar; escape sel formula saat export ketiga entitas.
7. **VAL-UOM** (`schemas.py` `UOMPayload.factor_to_base=Field(gt=0)` + handler `routers/uoms.py`). **ONBOARD-NOOP** (`routers/onboarding.py`): validasi `task_id` terhadap `ROLE_CHECKLISTS`.
8. **INV-GL-DRIFT** (`seed_realistic.py`): panggil `post_inventory_opening_balance` di akhir seed (idempotent) → subledger==GL.

## Cara verifikasi ulang
```bash
python seed_realistic.py
python scripts/verify_data_integrity.py            # PASS 123 / FAIL 0 / WARN 1
python forensic/fa_coverage_gap.py                 # PRET-GL, VB-CANCEL-GL -> [OK]
python seed_realistic.py && python forensic/fa_landed_cost_value.py   # GL 1-1300 Δ = alokasi
python seed_realistic.py && python forensic/fa_idor_matrix.py         # LEAK=0 dua arah
python seed_realistic.py && python forensic/fa_s074_errorpath.py      # 180 4xx / 0 crash / 0 noop
python seed_realistic.py && python forensic/fa_import_fuzz.py         # non-UTF8/neg/inf/xss ditolak
```

## Sisa follow-up (disarankan, tidak dikerjakan sesi ini)
1. **COGS-ZERO (P2):** pastikan `unit_cost` roll/cost snapshot terisi saat fulfillment agar `post_order_cogs` menghasilkan HPP; kini sudah dipagari WARN oleh gate.
2. **FE-A11Y-DIALOG (P3):** tambah `DialogTitle` (VisuallyHidden) pada dialog Radix terkait.
3. **IMP-XENT-CLOBBER (observasi):** tampilkan diff nilai lama saat import meng-overwrite SKU SHARED (audit trail), bila diinginkan.
4. **VB-PAY / cash lain:** pertimbangkan posting GL inline seragam (kini benar via backfill) untuk konsistensi.
