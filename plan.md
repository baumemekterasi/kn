# Development Plan — Finance Roadmap (Status: P1 ✅, P2 ✅, P6 ✅, P7 ✅; Gelombang-3 F-7/F-8/F-9 ✅; WAREHOUSE Fase A ✅, Fase B ✅, RFID Fase 5 ✅ (Simulator: Tags/Devices/Gate/Lokasi); Next: P3 SMTP PO PDF)

> **Update Session #074 (3 Jul 2026) — REPO RESTORE + POS "Minta Harga Khusus" (checkout shortcut) SELESAI & GREEN + tech-debt file-size DIBERESKAN:**
>
> - **Restore:** repo di-clone ulang dari GitHub (`bodyfullliquer/kn`) ke `/app` (‑preserve `.env`), deps backend (pip) + frontend (yarn) di-install, services RUNNING. `bash scripts/seed_reset.sh` = **LULUS** (contract/api_contract/integrity/entity-scoping), health_check 21 PASS/0 FAIL, endpoint_sweep **0×5xx**.
> - **Fitur checkout shortcut Harga Khusus (lanjutan sesi sebelumnya):** tombol per-item `request-special-price-<pid>` + modal `RequestSpecialPriceModal` (sales→Ajukan/pending; admin/manager→Setujui & Terapkan). Backend chain `create → approve → /effective` DIVERIFIKASI via curl (has_special=true, harga khusus benar; sales approve = **403**).
> - **BUG FIX (notice hilang):** notice `cart-item-sp-notice-<pid>` dulu ter-gate `!isSpecial` → setelah approve, badge muncul (isSpecial=true) sehingga notice ikut hilang (hanya flash ~400ms). Kini notice dirender bila `(notice || !isSpecial)` → **notice + badge tampil bersamaan**. Diverifikasi via Playwright: notice "Harga khusus Rp 100.000 disetujui & diterapkan." + badge struck-price tampil bersama. testing_agent_v3 iter_107 = FE 95% (bug ini), iter_108 = BE 100% + code-review OK.
> - **Tech-debt file-size DIBERESKAN (validate_compliance kini 94 PASS / 0 FAIL):**
>   - `CheckoutDrawer.jsx` 509→**496** — kartu item step-2 diekstrak ke `features/pos/CheckoutItemCard.jsx` (semua data-testid dipertahankan) + helper `Row` dipindah ke sana.
>   - `sales_orders.py` 832→**793** — body `frequent_products` diekstrak ke `services/sales_order_helpers.py::compute_frequent_products` (perilaku identik; endpoint tetap 200).
> - **Tech-debt tersisa (pre-existing, bukan dari sesi ini):** BiFinanceView.jsx empty-state (ux_audit ERROR, migration backlog).


> **Update Session #073 (2 Jul 2026) — RFID SIMULATOR (Fase 5) SELESAI & GREEN (4 menu cs-rfid-* LIVE):**
>
> - **4 menu di-wire** (dulu placeholder comingSoon): `Lokasi RFID` (cs-rfid-lokasi), `Tags tag↔item` (cs-rfid-tags), `Devices Reader/Gate` (cs-rfid-devices, admin-only), `Gate Monitor` (cs-rfid-gate). Grup nav "RFID & Traceability" kini LIVE (bukan Segera Hadir).
> - **Backend baru:** `routers/rfid.py` (197 baris) + `services/rfid_service.py`. 15 endpoint: summary, tags list/untagged/encode/auto-encode/retire, devices list/CRUD/seed-defaults, reads list, gate/simulate, reader/scan, locations.
> - **Koleksi baru:** `rfid_tags` (tag↔roll, SCOPED owner_entity_id), `rfid_devices` (SHARED infra per-gudang), `rfid_reads` (event log). Terdaftar di CANONICAL_COLLECTIONS + ENTITY_REGISTRY.md (L0 gate LULUS).
> - **Roll-as-SSOT DIJAGA:** encode hanya set `inventory_rolls.rfid_tag_id` + `tracking_mode="rfid"`; gate/scan hanya catat event + `last_seen`. TIDAK ada `$inc inventory_balances`. Diverifikasi: balance & roll-remaining tak berubah (3715.0 / 3935.0 konstan).
> - **Logika Gate (hijau/merah):** OUT gate → reserved/allocated/in_transit=HIJAU, available/quarantine=MERAH; IN gate → in_transit=HIJAU, lainnya=INFO. Drift lokasi terdeteksi (last-seen beda gudang).
> - **RBAC:** GET=wms:view; encode/retire/scan=wms:scan (warehouse/manager/admin); device write+seed=admin-only. Warehouse ditolak (403) di write device — terverifikasi.
> - **Seed:** `seed_rfid()` di seed_realistic (9 device, 40 tag on-hand, 40+ read incl. 1 hijau + 1 merah + 1 drift). Idempotent seed-defaults & auto-encode juga tersedia via UI.
> - **Verifikasi:** POC `test_rfid_poc.py` 24/24 PASS. testing_agent_v3 iter_104 = BE 92.9% (2 gagal = endpoint /inventory/summary milik test agent, BUKAN RFID), FE 100% (4 view render + interaksi OK). Guardrails: seed+gates LULUS, endpoint_sweep 0×5xx, ux_audit new-file lolos, rfid.py compliance PASS.
> - **Tech-debt tersisa (pre-existing, BUKAN dari RFID):** sales_orders.py 832 & CheckoutDrawer.jsx 509 (>batas), BiFinanceView.jsx empty-state (ux_audit).

> **Update Session #072 (2 Jul 2026) — WAREHOUSE Fase B SELESAI (Location/Putaway B1 + Reorder/ROP B2 WIRED & GREEN):**
>
> - **B1 Location & Putaway:** `LocationPutawayView.jsx` kini **di-wire ke `App.js`** (import + render block `activeView === "wms-locations"`, pola sama `StockAnalyticsView`). Menu "Lokasi & Putaway" (`wms-locations`, role admin/warehouse/manager) LIVE. Editor Zone→Rack→Level→Bin (tambah/hapus/edit + kapasitas) + tab Putaway (okupansi bin + antrean roll + aksi Tempatkan). Backend: `GET/PUT /api/warehouses/{id}/locations|structure`, `GET /api/inventory/putaway/queue`, `POST /api/inventory/putaway` (SSOT-safe: hanya ubah `inventory_rolls.bin_id`, TIDAK `$inc inventory_balances`).
> - **B2 Reorder/ROP:** `GET /api/purchase-requisitions/reorder-suggestions` ter-enhance velocity (avg_daily_sold, suggested_rop, lead_time, preferred_supplier).
> - **Bug fix saat wiring (3, semua terverifikasi):**
>   1. `WarehouseStructure.jsx` (overview di InventoryStockView) crash "reading 'code'" utk skema baru rack.levels[].bins → kini flatten dukung 2 skema (rack.bins lama & rack.levels[].bins baru) + guard + empty-state.
>   2. `LocationPutawayView.jsx` input nama zone/rack pakai `setField` rusak (`node[""][zi]`) → diganti pola `update()` onChange bersih (semua input konsisten).
>   3. Permission: role **warehouse** `warehouse:[view,create,update]` & **manager** `[view,create,update,export]` (sebelumnya hanya view → 403 saat putaway/save struktur). Update di `permissions_config.py` + doc `permission_settings` DB.
> - **Verifikasi:** seed_reset gates LULUS (contract/api_contract/integrity/entity-scoping), health_check 21/0/0, endpoint_sweep 0×5xx, ux_audit new-file lolos. testing_agent_v3 iter_103 = **BE 100% (9/9), FE 100%, 3/3 regression fix verified**. SSOT: putaway roll-based (balance = Σrolls, no drift).
> - **Fase B berikutnya (belum):** RFID (simulator, 4 menu `cs-rfid-*` masih placeholder).

> **Update Session #071 (2 Jul 2026) — WAREHOUSE (Fase A hardening + Fase B mulai):**
>
> **Fase B — Stock Analytics (Fast/Slow/Dead) ✅ (fitur baru, menu `cs-stock-analytics` kini LIVE):**
> - Service baru `services/stock_analytics_service.py` (READ-ONLY, entity-scoped): klasifikasi per-SKU by **hari sejak penjualan terakhir** (`outbound_ship`+`outbound_dispatch`) — Fast ≤ fast_max, Slow ≤ slow_max, Dead > slow_max; never-sold → di-downgrade ke Slow. + aging buckets (umur roll) + nilai (Σ length×base_unit_cost) + velocity/coverage. Ambang **configurable** di `config_service.inventory.stock_analytics` (default 30/90/90) — tak ada hardcode.
> - Endpoint `GET /api/inventory/stock-analytics?entity_id&warehouse_id&category` (di `inventory.py`, perm product:view). Tidak duplikat: `/reports/stock-aging` (widget manager) tetap; ini kanonik utk view Fase 5.
> - FE `features/inventory/StockAnalyticsView.jsx` (KPI klik-filter, Pie distribusi nilai, Bar aging, tabel + search/warehouse/category). App.js LIVE_CS_VIEWS + nav diaktifkan.
> - **Verifikasi:** api_contract OK, ux_audit new-file lolos, testing_agent iter_101 = **BE 100% (8/8), FE 95% (21/23)** — read-only integrity 119/0; 2 isu LOW = artefak dev (webpack overlay/Radix timing), bukan bug fungsi.
> - Fase B berikutnya (belum): struktur lokasi Zone→Rack→Level→Bin + putaway; Reorder/ROP + auto-PR; RFID (simulator).
>
> **Fase A — HARDENING (roll-as-SSOT, KN_15 §9/§10):** Deep-dive Warehouse menemukan 4 jalur lama yang melanggar SSOT (mutasi `inventory_balances` via `$inc` tanpa memindah/menyesuaikan `inventory_rolls` → drift `balance != Σrolls`). Dibuktikan empiris: menjalankan flow lama membuat `verify_data_integrity.py` 119/0 → 117/2 (INV-ROLL-1 FAIL). **FIX (terverifikasi):**
> - **D1 Transfer antar-gudang** (`transfers.py` + `roll_service`): kini roll-based berjenjang (reserve@create → dispatch:`in_transit_transfer` → complete: pindah `warehouse_id`, owner tetap; batal/tolak: release). Fungsi baru: `reserve_rolls_for_wh_transfer`/`dispatch_wh_transfer_rolls`/`receive_wh_transfer_rolls`/`release_wh_transfer_rolls`/`resolve_stock_owner`. Validasi stok → HTTP 409.
> - **D2 Cycle count** (`cycle_count.py`): owner-aware; adjustment via ROLL (`apply_cycle_count_adjustment`: surplus=buat roll, susut=kurangi roll FEFO) + `rebuild_balance`. Movement `cycle_count_adjustment` kini roll-linked.
> - **D3 Inbound manual** (`wms.py /wms/tasks`): membuat `inventory_roll` (`create_inbound_roll`) — bukan `$inc` balance.
> - **D4**: hapus dead code `inventory_service` (`allocate_stock`/`atomic_reserve`/`rollback_reservations`).
> - **D6 di-retract** (bukan bug — dispatch pakai `ship_order_rolls` yang SSOT-safe).
> - FE koheren: `TransferDetailModal` tampilkan lot/roll/owner; `CycleCount` tampilkan pemilik; error 409 tersurface.
> - **Verifikasi:** integrity gate 62/0 (×3 setelah D1/D2/D3), testing_agent_v3 iter_100 = **BE 100% (26/26), FE tanpa bug fungsional**, regresi inter-company transfer aman. Regression test: `backend/test_roll_ssot.py`.
> - **Next Warehouse (Fase B, belum):** struktur lokasi Zone→Rack→Level→Bin + putaway; Stock Analytics (fast/slow/dead >90h); Reorder/ROP; RFID (simulator).

> **Update Session #070 (2 Jul 2026):** Gelombang-3 penutup **F-7 (unifikasi costing)**, **F-8 (workflow Suspense 1-9999: report + reclass, tab di Buku Besar)**, **F-9 (closing tahunan di atas bulanan = residual, + STALE + Tutup Ulang/reclose)** SELESAI end-to-end. Gate hijau (api_contract 0 ERR, integrity 119/0 — FKT diperbarui utk DPP Nilai Lain). testing_agent_v3 iter_99: BE 13/13 + FE 100%, 0 bug. Detail: memory/SESSION_HANDOFF.md #070 + memory/FORENSIC_AUDIT_2026-06.md.


## 1) Objectives

### Status Saat Ini
- ✅ Modul **Laporan Keuangan** (Laba-Rugi & Neraca) **sudah selesai** end-to-end:
  - Backend:
    - `GET /api/finance/income-statement`
    - `GET /api/finance/balance-sheet` (comparative via `compare_as_of`)
    - Export CSV: `GET .../export.csv` (keduanya)
  - Frontend: menu Keuangan → **Laporan Keuangan**
    - 2 tab (Laba-Rugi/Neraca)
    - Filter: date range + period picker (bulan/tahun)
    - Neraca comparative (kolom pembanding + delta)
    - Export CSV (download via axios blob)
  - Testing: `testing_agent_v3` **PASS 100% (13/13)**

- ✅ Modul **Tutup Buku / Closing** (bulanan & tahunan) **sudah selesai** end-to-end:
  - Backend:
    - Preview/Close/Reopen/List/Status
    - Jurnal penutup otomatis → **Laba Ditahan (3-2000)**
    - Proteksi overlap bulanan vs tahunan (anti double-close)
    - Locking **soft** (peringatan, tidak memblokir posting)
    - Reopen admin-only (void jurnal penutup + status `reopened`)
  - Frontend: menu Keuangan → **Tutup Buku (Closing)** aktif
    - Form close bulanan/tahunan + pratinjau closing lines
    - Riwayat closing + status + reopen
    - Selector entitas internal (closing wajib PT spesifik)
  - Soft-lock warning terpasang di **JournalEntryModal** (non-blocking)
  - Testing: `testing_agent_v3` lulus (backend tervalidasi; overlap-guard teruji; frontend OK; regresi aman)

- ✅ Modul **BI Keuangan** **sudah selesai** end-to-end:
  - Backend:
    - `GET /api/finance/bi?year=...&entity_id=...`
    - Output: monthly trend 12 bulan + KPI YTD + rasio + perbandingan antar-PT
    - Operasional memakai `income_statement` (exclude closing); rasio neraca pakai `balance_sheet`
  - Frontend: menu Analitik (BI) → **BI Keuangan** aktif
    - KPI cards (Pendapatan/Beban/Laba Bersih/Marjin)
    - Chart tren bulanan (recharts ComposedChart: Bar Pendapatan & Beban + Line Laba Bersih)
    - Kartu rasio (gross/net margin, current ratio, debt-to-equity)
    - Perbandingan antar PT: bar chart + tabel ringkas
    - Filter tahun + refresh
  - Testing: `testing_agent_v3` **SEMUA PASS** (backend + frontend), regresi aman

- ✅ Modul **P6 CRM Omnichannel (MVP manual)** **sudah selesai** end-to-end:
  - Backend:
    - Leads pipeline:
      - `GET /api/crm/leads`, `GET /api/crm/leads/board`
      - `POST /api/crm/leads`, `PATCH /api/crm/leads/{id}`, `DELETE /api/crm/leads/{id}`
      - `POST /api/crm/leads/{id}/convert` (lead → customer)
      - `GET /api/crm/pipeline-stats`
    - Interaksi omnichannel:
      - `GET /api/crm/interactions`, `POST /api/crm/interactions`, `DELETE /api/crm/interactions/{id}`
    - RBAC: modul `customer` (view/create/update), row-scope sales (owner_id/created_by_id)
  - Frontend:
    - `LeadsPipeline.jsx` (Kanban 5 stage + modal add/edit + convert)
    - `OmnichannelInteractions.jsx` (timeline/feed + filter + modal catat interaksi)
    - 2 tab baru di `CrmView.jsx`: **Leads** dan **Interaksi**
  - Testing: `testing_agent_v3` **LULUS** (Backend 18/19; 1 minor 422-vs-400 = perilaku standar FastAPI/Pydantic; Frontend 100%; regresi CRM aman)
  - Data state: noise test dibersihkan → tersisa **5 lead demo kurasi + 1 interaksi**

**Catatan data GL:** Data seed GL saat ini minimal (jurnal bertanggal 2026-07-01), sehingga laporan/BI dapat terlihat sparse, namun logika sudah akurat & neraca seimbang.

### Objective Berikutnya (Roadmap Berikutnya)
- (P3) SMTP PO PDF (Email Purchase Order PDF)
- (P4) Budget Control
- (P5) Multi-currency/FX
- ✅ (P6) **CRM Omnichannel (MVP manual)** — **DONE**
- ✅ (P7) **Konsolidasi Grup + Eliminasi Intercompany** — **DONE** (testing_agent_v3: backend 100% 15/15; frontend terverifikasi visual — tab Laba-Rugi/Neraca/Eliminasi, matriks Per-PT+Eliminasi+Konsolidasi, CRUD, auto-detect; regresi aman)
- ⏭️ (P3) **SMTP PO PDF (Email Purchase Order PDF)** — **NEXT**

**Keputusan user untuk P7:**
- Eliminasi intercompany: **keduanya** (auto-deteksi kandidat + eliminasi manual)
- Output: upgrade dashboard existing → kolom **Per-PT + Eliminasi + Konsolidasi** untuk **Laba-Rugi & Neraca**

**Fondasi existing yang akan dipakai (P7):**
- Backend:
  - `gl_service.consolidation(entity_ids, as_of)` + `_entity_financials`
  - `financial_statement_service.income_statement(start,end,scope)` (operasional — exclude closing)
  - `financial_statement_service.balance_sheet(as_of,scope)` (include closing)
- Frontend:
  - `frontend/src/features/finance/ConsolidationDashboard.jsx` (view existing, akan di-upgrade / dipoint ke view baru)

---

## 2) Implementation Steps

### Phase 0 — Baseline (Completed)
**Deliverables**
- ✅ Endpoint laporan keuangan:
  - `GET /api/finance/income-statement`
  - `GET /api/finance/balance-sheet` (comparative via `compare_as_of`)
  - CSV export: `.../export.csv`
- ✅ Frontend: menu Keuangan → **Laporan Keuangan**
- ✅ Testing pass & regresi GL aman

---

### Phase 1 — P1 Tutup Buku / Closing (Backend + Frontend) (COMPLETED)

#### 1.1 User stories (Tercapai)
1. ✅ Close bulanan (pindahkan laba rugi periode ke Laba Ditahan)
2. ✅ Close tahunan (finalisasi tahun fiskal)
3. ✅ Lihat daftar periode tertutup + status
4. ✅ Reopen periode (admin)
5. ✅ Peringatan soft saat posting jurnal pada periode tertutup

#### 1.2 Keputusan akuntansi (Tercapai)
- ✅ Granularitas: **Bulanan & Tahunan**
- ✅ Closing:
  - Buat **jurnal penutup otomatis**
  - Pindahkan **Laba Bersih** periode → **Laba Ditahan (3-2000)**
  - Simpan record closing dan tandai periode tertutup
- ✅ Locking: **soft warning** (tidak menolak posting)
- ✅ Reopen: **Ya**, admin-only (void jurnal penutup)

#### 1.3 Desain data (Diimplementasikan)
- ✅ Koleksi: `period_closings`
  - Fields inti: `id, entity_id, period_type, period_key, period_label, start_date, end_date, status, net_income, revenue_total, expense_total, journal_entry_id, journal_entry_number, closed_by/at, reopened_by/at, note, created_at, updated_at`

#### 1.4 Backend tasks (Selesai)
- ✅ `backend/services/closing_service.py` (list/preview/close/reopen/status + overlap guard)
- ✅ Update `backend/services/financial_statement_service.py`:
  - `_aggregate(..., include_closing=True|False)`
  - `income_statement(... include_closing=False)` default exclude jurnal penutup
  - `balance_sheet(... include_closing=True)` default include jurnal penutup
- ✅ Router `backend/routers/closing.py` + register di `backend/server.py`

#### 1.5 Frontend tasks (Selesai)
- ✅ `frontend/src/features/finance/ClosingView.jsx`
- ✅ Navigation: `cs-closing` → `closing`, `PAGE_META["closing"]`, render di `App.js`
- ✅ Soft-lock warning di `JournalEntryModal`

#### 1.6 Testing (Selesai)
- ✅ `testing_agent_v3`: tervalidasi end-to-end + regresi aman.

---

### Phase 2 — P2 BI Keuangan (Backend + Frontend) (COMPLETED)

#### 2.1 User stories (Tercapai)
1. ✅ Tren bulanan pendapatan/HPP/beban/laba
2. ✅ KPI YTD + rasio penting
3. ✅ Perbandingan antar PT

#### 2.2 Backend tasks (Selesai)
- ✅ `backend/services/finance_bi_service.py`
- ✅ Router `backend/routers/finance_bi.py` + register di `backend/server.py`

#### 2.3 Frontend tasks (Selesai)
- ✅ `frontend/src/features/finance/BiFinanceView.jsx`
- ✅ Navigation: `cs-bi-finance` → `bi-finance`, `PAGE_META["bi-finance"]`, render di `App.js`

#### 2.4 Testing (Selesai)
- ✅ `testing_agent_v3`: **SEMUA PASS** (backend + frontend) + regresi aman.

---

### Phase 3 — P6 CRM Omnichannel (MVP manual) (Backend + Frontend) (COMPLETED)

#### 3.1 Scope (sesuai keputusan user)
- ✅ Timeline interaksi (omnichannel): catatan manual untuk phone/email/whatsapp/meeting/chat/sms/other.
- ✅ Pipeline lead Kanban: stage `new → qualified → proposal → won → lost`.
- ✅ Tanpa integrasi API eksternal (MVP). Semua input manual.

#### 3.2 Desain data (Diimplementasikan)
- ✅ Koleksi: `crm_interactions`
  - `id, entity_id, customer_id?, customer_name?, lead_id?, channel, direction, subject, notes, occurred_at, follow_up_date?, created_by, created_by_id, created_at`
- ✅ Koleksi: `crm_leads`
  - `id, entity_id, name, company, phone, email, source, stage, est_value, owner_id, owner_name, notes, customer_id?, lost_reason?, created_by, created_by_id, created_at, updated_at, stage_changed_at`

#### 3.3 Backend tasks (Selesai)
- ✅ `backend/services/crm_omnichannel_service.py`:
  - CRUD lead + board kanban + pipeline stats
  - CRUD interaksi + filter
  - Konversi lead→customer (buat customer baru) + relink interaksi ke customer
  - Scoping: sales dibatasi owner/creator
- ✅ Router `backend/routers/crm_omnichannel.py` + register di `backend/server.py`

#### 3.4 Frontend tasks (Selesai)
- ✅ `frontend/src/features/crm/LeadsPipeline.jsx`
- ✅ `frontend/src/features/crm/OmnichannelInteractions.jsx`
- ✅ Tambah 2 tab di `frontend/src/features/crm/CrmView.jsx`: `Leads` dan `Interaksi`

#### 3.5 Testing (Selesai)
- ✅ `testing_agent_v3`: **LULUS** (backend 18/19; minor 422-vs-400 normal), frontend 100%.

**Deliverables P6**
- ✅ CRM Omnichannel MVP usable: pipeline leads + timeline interaksi manual.

---

### Phase 4 — P7 Konsolidasi Grup + Eliminasi Intercompany (Backend + Frontend) (COMPLETED)

#### 4.1 Scope (sesuai keputusan user)
- Upgrade dashboard konsolidasi existing untuk menampilkan:
  - **Per-PT**
  - **Eliminasi**
  - **Konsolidasi**
  untuk **Laba-Rugi & Neraca**.
- Eliminasi intercompany:
  - **Auto-deteksi kandidat** (heuristik akun/keyword + saldo)
  - **Eliminasi manual** (input jurnal eliminasi)

#### 4.2 Desain data (baru)
- Koleksi `intercompany_eliminations` (MVP draft):
  - `id, name, entity_group_id?, entity_from?, entity_to?, effective_date, note, type(pl|bs|both),`
  - `lines[{account_code, account_name?, debit, credit, description}],`
  - `created_by, created_by_id, created_at, updated_at`

> Catatan: untuk MVP, eliminasi diperlakukan sebagai adjustment konsolidasi (tidak memodifikasi journal_entries per-PT). Audit trail tetap via dokumen eliminasi.

#### 4.3 Backend tasks (to implement)
- Buat `backend/services/consolidation_service.py`:
  - Hitung **Per-PT P&L** berbasis `income_statement(year)` per entitas (operasional)
  - Hitung **Per-PT Neraca** berbasis `balance_sheet(as_of)` per entitas
  - Hitung **Eliminasi** dari koleksi `intercompany_eliminations`:
    - P&L eliminasi dipakai bila `effective_date` berada pada tahun yang diminta
    - Neraca eliminasi dipakai bila `effective_date <= as_of`
  - Klasifikasi impact baris eliminasi berdasarkan tipe akun (mengacu TB logic):
    - income → revenue (credit_net)
    - expense → cogs (kode mulai 5) / opex (lainnya)
    - asset → assets (debit_net)
    - liability → liabilities (credit_net)
    - equity → equity (credit_net)
  - Output konsolidasi:
    - `gross` = sum per-PT
    - `elimination` = total eliminasi
    - `consolidated` = gross + elimination
- Endpoint baru (router `backend/routers/consolidation.py`, prefix `/api`):
  - `GET /api/finance/consolidation/summary?as_of=YYYY-MM-DD&year=YYYY`
  - `GET /api/finance/consolidation/eliminations`
  - `POST /api/finance/consolidation/eliminations`
  - `DELETE /api/finance/consolidation/eliminations/{id}`
  - `GET /api/finance/consolidation/ic-candidates?as_of=YYYY-MM-DD`
    - Heuristik kandidat: akun dengan keyword (`intercompany`, `antar entitas`, `antar-pt`, `antarperusahaan`, `ic-`, `inter-co`) + saldo per-PT
    - Kembalikan saran baris eliminasi (reverse saldo)
- RBAC:
  - read summary/candidates: `accounting:view`
  - tulis eliminasi: `accounting:manage`
- Register router di `backend/server.py`.

#### 4.4 Frontend tasks (to implement)
- Buat view baru `frontend/src/features/finance/GroupConsolidationView.jsx` (atau upgrade file existing):
  - Tabs: **Laba-Rugi**, **Neraca**, **Eliminasi**
  - Filter: `year` (untuk P&L) dan `as_of` (untuk Neraca)
  - Matrix tampilan:
    - Tabel **Per-PT** (kolom tiap entitas)
    - Kolom **Eliminasi**
    - Kolom **Konsolidasi**
  - Panel Eliminasi:
    - daftar eliminasi
    - tambah eliminasi manual (form lines debit/kredit)
    - hapus eliminasi
    - panel **Deteksi Otomatis** (ic-candidates → “jadikan draft eliminasi”)
- Repoint route `consolidation` di `App.js` ke view baru, tetap pertahankan `ConsolidationDashboard.jsx` sebagai referensi/legacy.

#### 4.5 Testing (COMPLETED)
- ✅ `testing_agent_v3` (iteration_96):
  - Backend **100% PASS (15/15)**: summary (consolidated = gross + elimination, Neraca seimbang), CRUD eliminasi (create balanced/unbalanced, validasi empty→400, delete + 404), ic-candidates (auto-deteksi 2 akun), RBAC (view/manage), entity scoping.
  - Regresi backend aman: income-statement, balance-sheet, closing, BI, CRM leads.
  - Frontend: code review PASS (data-testid lengkap) + **verifikasi visual manual (screenshot)**: tab Laba-Rugi/Neraca/Eliminasi, matriks Per-PT+Eliminasi+Konsolidasi, badge Seimbang, panel Deteksi Otomatis, CRUD eliminasi.
  - Data demo pristine (1 eliminasi demo tersisa).

**Deliverables P7**
- Konsolidasi grup dengan lapisan eliminasi (manual + auto-detect kandidat) dan output Per-PT + Eliminasi + Konsolidasi untuk P&L 8 Neraca.

---

## 3) Next Actions (urutan eksekusi)
1. ✅ (P1) Closing end-to-end selesai.
2. ✅ (P2) BI Keuangan end-to-end selesai.
3. ✅ (P6) CRM Omnichannel (manual) selesai.
4. ⏭️ **(P7) Konsolidasi + Eliminasi Intercompany** — implement backend+frontend+testing.
5. ⏭️ Lanjut roadmap lain:
   - (P3) SMTP PO PDF
   - (P4) Budget Control
   - (P5) Multi-currency/FX

---

## 4) Success Criteria

### P6 CRM Omnichannel (Achieved)
- ✅ Lead pipeline Kanban (5 stage) berfungsi (create/edit/move/convert).
- ✅ Timeline interaksi manual tersimpan dan ter-filter.
- ✅ RBAC konsisten (`customer:view|create|update`) + row-scope sales.
- ✅ Tidak ada regresi pada modul CRM existing.

### P7 Konsolidasi + Eliminasi Intercompany (Target)
- Dashboard konsolidasi menampilkan Per-PT + Eliminasi + Konsolidasi untuk P&L dan Neraca.
- Eliminasi dapat:
  - diinput manual (draft)
  - diawali dari kandidat auto-detect
- Output konsolidasi tetap seimbang (neraca) dan audit trail tersedia.

### Housekeeping / Data State
- ✅ Cleanup: record uji `period_closings` & jurnal penutup void dihapus → state demo pristine.
- ✅ Cleanup P6: noise test CRM dihapus → tersisa 5 lead demo kurasi + 1 interaksi.

> Catatan pembatas: jangan mengubah `REACT_APP_BACKEND_URL` / `MONGO_URL`.
