import {
  AlertTriangle,
  ArrowLeftRight,
  BarChart3,
  BarChart2,
  Bell,
  BookOpen,
  Boxes,
  Calculator,
  CalendarDays,
  CalendarX,
  Timer,
  ClipboardCheck,
  ClipboardList,
  Clock,
  CreditCard,
  Cpu,
  DollarSign,
  FileText,
  FileStack,
  FileBarChart,
  Home,
  IdCard,
  Layers3,
  LineChart,
  MapPin,
  Navigation,
  Network,
  Palette,
  Percent,
  PieChart,
  Printer,
  Receipt,
  RotateCcw,
  Route,
  Landmark,
  Settings,
  Settings2,
  ShieldCheck,
  ShoppingBag,
  ShoppingCart,
  Star,
  Tag,
  Target,
  TrendingUp,
  TrendingDown,
  Truck,
  UserCheck,
  Users,
  Wallet,
  Warehouse,
  Wifi,
} from "lucide-react";

// ─── PAGE META (SSOT untuk TopBar kicker + title) ─────────────────────────────
export const PAGE_META = {
  admin:                  { kicker: "Pengaturan",     title: "Master Data & Audit" },
  "admin-home":           { kicker: "Eksekutif",      title: "Control Tower" },
  sales:                  { kicker: "Penjualan",      title: "POS / Sales Portal" },
  "sales-home":           { kicker: "Penjualan",      title: "Performa Saya" },
  "customers-crm":        { kicker: "Penjualan",      title: "Pelanggan & CRM \u00b7 Sales Force" },
  "price-approvals":      { kicker: "Approvals",      title: "Approval Harga Khusus" },
  orders:                 { kicker: "Penjualan",      title: "Pesanan Penjualan" },
  "tax-invoices":         { kicker: "Keuangan \u00b7 Pajak", title: "Faktur Pajak Keluaran" },
  "returns":              { kicker: "Penjualan",      title: "Returns & Barang Sisa" },
  "special-orders":       { kicker: "Penjualan",      title: "Special Order (OD)" },
  "pricelist":            { kicker: "Penjualan",      title: "Pricelist per-Entitas (PT)" },
  "product-templates":    { kicker: "Penjualan",      title: "Template & Varian Produk" },
  "approval-inbox":       { kicker: "Approvals",      title: "Pusat Persetujuan" },
  "approval-rules":       { kicker: "Pengaturan",     title: "Approval Rules" },
  purchasing:             { kicker: "Pembelian",      title: "Pesanan Pembelian (PO)" },
  "blanket-po":           { kicker: "Pembelian",      title: "Blanket / Contract PO · Call-off" },
  "purchase-requisitions":{ kicker: "Pembelian",      title: "Purchase Requisition (PR)" },
  reorder:                { kicker: "Pembelian",      title: "Saran Reorder · Replenishment" },
  suppliers:              { kicker: "Pembelian",      title: "Master Pemasok (Supplier)" },
  "purchase-approval":    { kicker: "Approvals",      title: "Approval Pembelian" },
  "cash-management":      { kicker: "Keuangan",       title: "Transaksi Kas" },
  "purchase-returns":     { kicker: "Pembelian",      title: "Retur Beli (Nota Debit)" },
  "vendor-bills":         { kicker: "Pembelian",      title: "Tagihan Supplier · 3-Way Matching" },
  "landed-cost":          { kicker: "Pembelian",      title: "Landed Cost · Alokasi HPP Roll" },
  "input-tax":            { kicker: "Keuangan \u00b7 Pajak", title: "Faktur Pajak Masukan · PPN Masukan & Rekap" },
  "rfq":                  { kicker: "Pembelian",      title: "RFQ / Quotation · Tender & Banding Harga Supplier" },
  operations:             { kicker: "Gudang",         title: "Operasi Gudang (WMS)" },
  "qc-inspection":        { kicker: "Gudang",         title: "Inspeksi QC · Penerimaan" },
  "inventory-board":      { kicker: "Gudang",         title: "Status Stok & ATP" },
  "stock-buckets":        { kicker: "Gudang",         title: "Stok Multi-Bucket (WIP / Hold / In-transit)" },
  "interco-transfers":    { kicker: "Gudang",         title: "Transfer Antar-Entitas" },
  escalations:            { kicker: "Eskalasi",       title: "Eskalasi Inbound & Outbound" },
  documents:              { kicker: "Dokumen",        title: "Print Center & Labels" },
  reports:                { kicker: "Analitik",       title: "Dashboard & Analytics" },
  costing:                { kicker: "Analitik (BI)",  title: "Margin & HPP (WAC)" },
  // Coming Soon views (cs-* yang benar-benar belum live)
  "cs-price-list":        { kicker: "Penjualan",      title: "Price List per Customer" },
  "cs-bom":               { kicker: "Pembelian",      title: "BOM Printing" },
  "cs-stock-analytics":   { kicker: "Gudang",         title: "Stock Analytics (Fast/Slow/Dead)" },
  "wms-locations":        { kicker: "Gudang",         title: "Lokasi Gudang & Putaway" },
  "cs-rfid-lokasi":       { kicker: "RFID",           title: "Lokasi RFID" },
  "cs-rfid-tags":         { kicker: "RFID",           title: "Tags (tag↔item)" },
  "cs-rfid-devices":      { kicker: "RFID",           title: "Devices (Reader / Gate)" },
  "cs-rfid-gate":         { kicker: "RFID",           title: "Gate Monitor" },
  "chart-of-accounts":    { kicker: "Keuangan",       title: "Bagan Akun · Chart of Accounts" },
  "general-ledger":       { kicker: "Keuangan",       title: "Buku Besar · Jurnal Umum" },
  "financial-statements": { kicker: "Keuangan",       title: "Laporan Keuangan · Laba-Rugi & Neraca" },
  "bank-accounts":        { kicker: "Keuangan",       title: "Kas & Bank · Rekening & Saldo" },
  "cs-pajak":             { kicker: "Keuangan \u00b7 Pajak", title: "PPh & Rekap Pajak" },
  "ar-aging":             { kicker: "Keuangan",       title: "AR / Piutang & Aging" },
  "consolidation":        { kicker: "Keuangan",       title: "Konsolidasi Grup · Eliminasi Intercompany" },
  "closing":              { kicker: "Keuangan",       title: "Tutup Buku · Closing Bulanan & Tahunan" },
  "hr-employees":         { kicker: "SDM (HRD)",      title: "Karyawan" },
  "hr-org-units":         { kicker: "SDM (HRD)",      title: "Struktur Organisasi" },
  "hr-my-profile":        { kicker: "SDM (HRD)",      title: "Profil Saya (ESS)" },
  "hr-attendance":        { kicker: "SDM (HRD)",      title: "Presensi & Kehadiran" },
  "hr-attendance-setup":  { kicker: "SDM (HRD)",      title: "Shift & Geofence" },
  "hr-live-tracking":     { kicker: "SDM (HRD)",      title: "Lacak Lapangan · Live Tracking Sales" },
  "hr-visits":            { kicker: "Penjualan",      title: "Kunjungan Sales (Visit)" },
  "hr-payroll-runs":      { kicker: "SDM (HRD)",      title: "Payroll Run · Penggajian" },
  "hr-payslips":          { kicker: "SDM (HRD)",      title: "Slip Gaji (Payslip)" },
  "hr-payroll-setup":     { kicker: "SDM (HRD)",      title: "Setup Gaji, BPJS & PPh21" },
  "hr-leave":             { kicker: "SDM (HRD)",      title: "Cuti & Izin" },
  "hr-overtime":          { kicker: "SDM (HRD)",      title: "Lembur (Overtime)" },
  "cs-kpi":               { kicker: "SDM (HRD)",      title: "KPI Design" },
  "cs-design-gallery":    { kicker: "SDM (HRD)",      title: "Design Gallery + AI" },
  "cs-bi-sales":          { kicker: "Analitik (BI)",  title: "Dashboard BI Sales" },
  "cs-bi-stock":          { kicker: "Analitik (BI)",  title: "Dashboard BI Stok" },
  "bi-finance":           { kicker: "Analitik (BI)",  title: "BI Keuangan · Tren, Rasio & Perbandingan PT" },
  "cs-bi-hrd":            { kicker: "Analitik (BI)",  title: "Dashboard BI SDM" },
};

// ─── HUB TABS (Restrukturisasi IA — Opsi A) ───────────────────────────────────
// Satu menu = satu proses bisnis; variasi/langkahnya menjadi TAB (bar sekunder di
// atas view). view = activeView yang di-render App.js (komponen TIDAK berubah,
// deep-link lama tetap hidup). tab = khusus operations (sub-tab internal WMS).
export const HUB_TABS = {
  "approval-inbox": [
    { view: "approval-inbox",    label: "Inbox Persetujuan",     roles: ["manager", "admin"] },
    { view: "price-approvals",   label: "Approval Harga",        roles: ["admin", "sales", "manager"] },
    { view: "purchase-approval", label: "Approval Pembelian",    roles: ["admin", "manager"] },
  ],
  "sales-orders": [
    { view: "orders",            label: "Pesanan (SO)",          roles: ["admin", "sales", "manager"] },
    { view: "returns",           label: "Retur & Barang Sisa",   roles: ["admin", "sales", "manager"] },
    { view: "special-orders",    label: "Special Order (OD)",    roles: ["admin", "sales", "manager"] },
  ],
  "customers-crm": [
    { view: "customers-crm",     label: "CRM & Pelanggan",       roles: ["admin", "sales", "manager"] },
    { view: "hr-visits",         label: "Kunjungan Sales",       roles: ["admin", "sales", "manager"] },
  ],
  "products-pricing": [
    { view: "product-templates", label: "Template & Varian",     roles: ["admin", "manager"] },
    { view: "pricelist",         label: "Pricelist per-PT",      roles: ["admin", "manager"] },
  ],
  "sourcing": [
    { view: "reorder",               label: "Saran Reorder",     roles: ["admin", "manager"] },
    { view: "purchase-requisitions", label: "Purchase Requisition", roles: ["admin", "manager", "warehouse"] },
    { view: "rfq",                   label: "RFQ / Quotation",   roles: ["admin", "manager", "warehouse"] },
  ],
  "purchase-orders": [
    { view: "purchasing",        label: "Pesanan Pembelian (PO)", roles: ["admin", "manager"] },
    { view: "blanket-po",        label: "Blanket / Kontrak",     roles: ["admin", "manager"] },
  ],
  "accounts-payable": [
    { view: "vendor-bills",      label: "Tagihan Supplier",      roles: ["admin", "manager"] },
    { view: "landed-cost",       label: "Landed Cost (HPP)",     roles: ["admin", "manager"] },
    { view: "purchase-returns",  label: "Retur Beli (Nota Debit)", roles: ["admin", "manager", "warehouse"] },
  ],
  "wms-operations": [
    { view: "operations",        label: "Operasi WMS",           roles: ["admin", "warehouse", "manager", "sales"] },
    { view: "qc-inspection",     label: "Inspeksi QC",           roles: ["admin", "warehouse", "manager"] },
    { view: "interco-transfers", label: "Transfer Antar-Entitas", roles: ["admin", "warehouse", "manager"] },
  ],
  "stock-atp": [
    { view: "inventory-board",   label: "Status Stok & ATP",     roles: ["admin", "warehouse", "manager", "sales"] },
    { view: "stock-buckets",     label: "Stok Multi-Bucket",     roles: ["admin", "warehouse", "manager"] },
  ],
  "cash-bank": [
    { view: "bank-accounts",     label: "Rekening & Saldo",      roles: ["admin", "manager"] },
    { view: "cash-management",   label: "Transaksi Kas",         roles: ["admin", "manager"] },
  ],
  "tax-hub": [
    { view: "tax-invoices",      label: "Faktur Keluaran",       roles: ["admin", "manager"] },
    { view: "input-tax",         label: "Faktur Masukan",        roles: ["admin", "manager"] },
    { view: "cs-pajak",          label: "PPh & Rekap",           roles: ["admin", "manager"] },
  ],
  "ledger": [
    { view: "general-ledger",    label: "Jurnal & Buku Besar",   roles: ["admin", "manager"] },
    { view: "chart-of-accounts", label: "Chart of Accounts",     roles: ["admin", "manager"] },
  ],
  "fin-reports": [
    { view: "financial-statements", label: "Laba-Rugi & Neraca", roles: ["admin", "manager"] },
    { view: "consolidation",        label: "Konsolidasi Grup",   roles: ["admin", "manager"] },
  ],
  "hr-people": [
    { view: "hr-employees",      label: "Karyawan",              roles: ["admin", "manager"] },
    { view: "hr-org-units",      label: "Struktur Organisasi",   roles: ["admin", "manager"] },
  ],
  "hr-attendance-hub": [
    { view: "hr-attendance",       label: "Presensi",            roles: ["admin", "manager"] },
    { view: "hr-leave",            label: "Cuti & Izin",         roles: ["admin", "manager"] },
    { view: "hr-overtime",         label: "Lembur",              roles: ["admin", "manager"] },
    { view: "hr-live-tracking",    label: "Lacak Lapangan",      roles: ["admin", "manager"] },
    { view: "hr-attendance-setup", label: "Shift & Geofence",    roles: ["admin", "manager"] },
  ],
  "hr-payroll-hub": [
    { view: "hr-payroll-runs",   label: "Payroll Run",           roles: ["admin", "manager"] },
    { view: "hr-payslips",       label: "Slip Gaji",             roles: ["admin", "manager"] },
    { view: "hr-payroll-setup",  label: "Setup Penggajian",      roles: ["admin", "manager"] },
  ],
  "hr-kpi-hub": [
    { view: "cs-kpi",            label: "KPI Design",            roles: ["admin", "manager"] },
    { view: "cs-design-gallery", label: "Design Gallery + AI",   roles: ["admin", "manager"] },
  ],
  "analytics": [
    { view: "reports",           label: "Overview",              roles: ["admin", "manager"] },
    { view: "costing",           label: "Margin & HPP",          roles: ["admin", "manager"] },
    { view: "bi-finance",        label: "BI Keuangan",           roles: ["admin", "manager"] },
    { view: "cs-bi-hrd",         label: "BI SDM",                roles: ["admin", "manager"] },
  ],
  "settings-hub": [
    { view: "admin",             label: "Master Data & Audit",   roles: ["admin"] },
    { view: "approval-rules",    label: "Approval Rules",        roles: ["admin"] },
  ],
};

export function hubTabsForRole(hubId, role) {
  return (HUB_TABS[hubId] || []).filter((t) => !t.roles || t.roles.includes(role));
}

// view → hubId (untuk render tab bar & highlight sidebar)
const HUB_VIEW_INDEX = (() => {
  const idx = {};
  for (const [hubId, tabs] of Object.entries(HUB_TABS)) {
    tabs.forEach((t) => { idx[t.view] = hubId; });
  }
  return idx;
})();

export function hubForView(view, role) {
  const hubId = HUB_VIEW_INDEX[view];
  if (!hubId) return null;
  const tabs = hubTabsForRole(hubId, role);
  if (!tabs.length || !tabs.some((t) => t.view === view)) return null;
  return { hubId, tabs };
}

// ─── NAV STRUCTURE (IA v2 — hub-and-tab, 7±2 per grup, urutan = alur proses) ──
const NAV_STRUCTURE = [

  // ── BERANDA ──────────────────────────────────────────────────────────────────
  {
    type: "standalone",
    id:    "home",
    label: "Beranda",
    icon:  Home,
    roles: ["admin", "sales", "manager", "warehouse"],
    view:  null,  // App.js resolve via defaultViewForRole
  },

  // ── PUSAT PERSETUJUAN (satu pintu semua approval) ────────────────────────────
  {
    type: "standalone",
    id:    "approval-inbox",
    label: "Pusat Persetujuan",
    icon:  Bell,
    roles: ["manager", "admin", "sales"],
    hub:   "approval-inbox",
  },

  // ── PENJUALAN ────────────────────────────────────────────────────────────────
  {
    type:    "group",
    groupId: "penjualan",
    label:   "Penjualan",
    icon:    ShoppingCart,
    roles:   ["admin", "sales", "manager"],
    items: [
      { id: "sales",            label: "POS / Sales Portal", icon: ShoppingBag, roles: ["admin", "sales"] },
      { id: "sales-orders",     label: "Pesanan & Retur",    icon: FileText,    roles: ["admin", "sales", "manager"], hub: "sales-orders" },
      { id: "customers-crm",    label: "Pelanggan & CRM",    icon: Users,       roles: ["admin", "sales", "manager"], hub: "customers-crm" },
      { id: "products-pricing", label: "Produk & Harga",     icon: Layers3,     roles: ["admin", "manager"],          hub: "products-pricing" },
      { id: "cs-price-list",    label: "Price List per Customer", icon: Tag,    roles: ["admin", "manager"], comingSoon: true },
    ],
  },

  // ── PEMBELIAN ────────────────────────────────────────────────────────────────
  {
    type:    "group",
    groupId: "pembelian",
    label:   "Pembelian",
    icon:    ClipboardList,
    roles:   ["admin", "manager", "warehouse"],
    items: [
      { id: "sourcing",         label: "Pengadaan (Sourcing)",    icon: Target,        roles: ["admin", "manager", "warehouse"], hub: "sourcing" },
      { id: "purchase-orders",  label: "Pesanan Pembelian (PO)",  icon: ClipboardList, roles: ["admin", "manager"],              hub: "purchase-orders" },
      { id: "suppliers",        label: "Pemasok (Supplier)",      icon: Truck,         roles: ["admin", "manager"] },
      { id: "accounts-payable", label: "Hutang Supplier (AP)",    icon: Receipt,       roles: ["admin", "manager", "warehouse"], hub: "accounts-payable" },
      { id: "cs-bom",           label: "BOM Printing",            icon: Printer,       roles: ["admin"], comingSoon: true },
    ],
  },

  // ── GUDANG ───────────────────────────────────────────────────────────────────
  {
    type:    "group",
    groupId: "gudang",
    label:   "Gudang",
    icon:    Warehouse,
    roles:   ["admin", "warehouse", "manager", "sales"],
    items: [
      { id: "wms-operations",     label: "Operasi Gudang (WMS)", icon: Warehouse, roles: ["admin", "warehouse", "manager", "sales"], hub: "wms-operations" },
      { id: "stock-atp",          label: "Stok & ATP",           icon: Boxes,     roles: ["admin", "warehouse", "manager", "sales"], hub: "stock-atp" },
      { id: "wms-locations",      label: "Lokasi & Putaway",     icon: MapPin,    roles: ["admin", "warehouse", "manager"] },
      { id: "cs-stock-analytics", label: "Stock Analytics",      icon: TrendingUp, roles: ["admin", "manager"] },
    ],
  },

  // ── RFID & TRACEABILITY (Fase 5 — SIMULATOR, LIVE) ──────────────────────────
  {
    type:    "group",
    groupId: "rfid",
    label:   "RFID & Traceability",
    icon:    Cpu,
    roles:   ["admin", "warehouse"],
    items: [
      { id: "cs-rfid-lokasi",  label: "Lokasi RFID",           icon: MapPin, roles: ["admin", "warehouse"] },
      { id: "cs-rfid-tags",    label: "Tags (tag↔item)",       icon: Tag,    roles: ["admin", "warehouse"] },
      { id: "cs-rfid-devices", label: "Devices (Reader/Gate)", icon: Wifi,   roles: ["admin"] },
      { id: "cs-rfid-gate",    label: "Gate Monitor",          icon: Cpu,    roles: ["admin", "warehouse"] },
    ],
  },

  // ── KEUANGAN (menyerap Kas dari Pembelian + Pajak 3-pintu jadi 1) ────────────
  {
    type:    "group",
    groupId: "keuangan",
    label:   "Keuangan",
    icon:    DollarSign,
    roles:   ["admin", "manager"],
    items: [
      { id: "cash-bank",   label: "Kas & Bank",            icon: CreditCard,   roles: ["admin", "manager"], hub: "cash-bank" },
      { id: "ar-aging",    label: "AR / Piutang & Aging",  icon: TrendingDown, roles: ["admin", "manager"] },
      { id: "tax-hub",     label: "Pajak (PPN & PPh)",     icon: Percent,      roles: ["admin", "manager"], hub: "tax-hub" },
      { id: "ledger",      label: "Buku Besar & CoA",      icon: FileStack,    roles: ["admin", "manager"], hub: "ledger" },
      { id: "fin-reports", label: "Laporan & Konsolidasi", icon: FileBarChart, roles: ["admin", "manager"], hub: "fin-reports" },
      { id: "closing",     label: "Tutup Buku (Closing)",  icon: CalendarX,    roles: ["admin", "manager"] },
    ],
  },

  // ── SDM (HRD) ────────────────────────────────────────────────────────────────
  {
    type:    "group",
    groupId: "hrd",
    label:   "SDM (HRD)",
    icon:    Users,
    roles:   ["admin", "manager"],
    items: [
      { id: "hr-people",         label: "Karyawan & Organisasi", icon: UserCheck,  roles: ["admin", "manager"], hub: "hr-people" },
      { id: "hr-attendance-hub", label: "Kehadiran & Cuti",      icon: Clock,      roles: ["admin", "manager"], hub: "hr-attendance-hub" },
      { id: "hr-payroll-hub",    label: "Payroll",               icon: Calculator, roles: ["admin", "manager"], hub: "hr-payroll-hub" },
      { id: "hr-kpi-hub",        label: "KPI & Design",          icon: Palette,    roles: ["admin", "manager"], hub: "hr-kpi-hub" },
    ],
  },

  // ── ANALITIK (satu hub) ──────────────────────────────────────────────────────
  {
    type:  "standalone",
    id:    "analytics",
    label: "Analytics Hub",
    icon:  BarChart3,
    roles: ["admin", "manager"],
    hub:   "analytics",
  },
  { type: "standalone", id: "cs-bi-sales", label: "BI Sales", icon: TrendingUp, roles: ["admin", "manager"], comingSoon: true },
  { type: "standalone", id: "cs-bi-stock", label: "BI Stok",  icon: PieChart,   roles: ["admin", "manager"], comingSoon: true },

  // ── UTILITAS & PENGATURAN ────────────────────────────────────────────────────
  {
    type:  "standalone",
    id:    "documents",
    label: "Print Center",
    icon:  Printer,
    roles: ["admin", "sales", "warehouse", "manager"],
    view:  "documents",
  },
  {
    type:  "standalone",
    id:    "settings-hub",
    label: "Pengaturan & Master Data",
    icon:  Settings,
    roles: ["admin"],
    hub:   "settings-hub",
  },
  {
    type:  "standalone",
    id:    "hr-my-profile",
    label: "Profil Saya",
    icon:  IdCard,
    roles: ["admin", "sales", "manager", "warehouse"],
    view:  "hr-my-profile",
  },
  {
    type:  "standalone",
    id:    "escalations",
    label: "Eskalasi",
    icon:  AlertTriangle,
    roles: ["admin", "warehouse", "manager"],
    view:  "escalations",
  },
];

// Untuk item hub: view default = tab pertama yang boleh diakses role tsb.
function withHubView(item, role) {
  if (!item.hub) return item;
  const tabs = hubTabsForRole(item.hub, role);
  return { ...item, view: tabs.length ? tabs[0].view : (item.view || item.id) };
}

// ─── BUILD GROUPED NAVIGATION — filter per role; comingSoon → grup "Segera Hadir" ──
export function buildNavGroups(role, opts = {}) {
  const showComingSoon = opts.showComingSoon !== false;
  const result = [];
  const comingSoonItems = [];
  for (const entry of NAV_STRUCTURE) {
    if (!entry.roles.includes(role)) continue;
    if (entry.type === "standalone") {
      if (entry.comingSoon) comingSoonItems.push(entry);
      else result.push(withHubView(entry, role));
    } else if (entry.type === "group") {
      const roleItems = entry.items.filter(item => item.roles.includes(role));
      const liveItems = roleItems.filter(item => !item.comingSoon).map(item => withHubView(item, role));
      const soonItems = roleItems.filter(item => item.comingSoon);
      if (liveItems.length > 0) result.push({ ...entry, items: liveItems });
      soonItems.forEach(item => comingSoonItems.push(item));
    }
  }
  if (showComingSoon && comingSoonItems.length > 0) {
    result.push({
      type: "group",
      groupId: "segera-hadir",
      label: "Segera Hadir",
      icon: Clock,
      roles: [role],
      comingSoonGroup: true,
      items: comingSoonItems,
    });
  }
  return result;
}

// Backward compat: flat array untuk komponen lama jika perlu
export function buildNavigation(role) {
  const groups = buildNavGroups(role);
  const flat = [];
  for (const entry of groups) {
    if (entry.type === "standalone") flat.push(entry);
    else entry.items.forEach(item => flat.push(item));
  }
  return flat;
}

// ─── COMMAND PALETTE ENTRIES (Ctrl+K) — semua tujuan navigasi role ini ─────────
export function buildPaletteEntries(role) {
  const entries = [];
  const seen = new Set();
  const push = (e) => {
    const key = `${e.view}::${e.tab || ""}`;
    if (seen.has(key)) return;
    seen.add(key);
    entries.push(e);
  };
  for (const entry of NAV_STRUCTURE) {
    if (!entry.roles.includes(role)) continue;
    const walk = (item, groupLabel) => {
      if (item.comingSoon) return;
      if (item.hub) {
        hubTabsForRole(item.hub, role).forEach((t) => push({
          navId: item.id, view: t.view, tab: t.tab,
          label: `${item.label} \u203a ${t.label}`, group: groupLabel, icon: item.icon,
        }));
      } else {
        push({ navId: item.id, view: item.view || item.id, tab: item.tab,
               label: item.label, group: groupLabel, icon: item.icon });
      }
    };
    if (entry.type === "standalone") walk(entry, "Umum");
    else entry.items.filter(i => i.roles.includes(role)).forEach(i => walk(i, entry.label));
  }
  return entries;
}

// ─── ROLE-HOME REGISTRY (F5) — landing per role ────────────────────────────────
export const ROLE_HOME_REGISTRY = {
  admin:     { view: "admin-home", navId: "home" },
  manager:   { view: "reports",    navId: "analytics" },
  warehouse: { view: "operations", navId: "wms-operations" },
  sales:     { view: "sales-home", navId: "home" },
};
export function defaultViewForRole(role, registry = ROLE_HOME_REGISTRY) {
  return (registry[role] || registry.sales).view;
}
export function defaultNavIdForRole(role, registry = ROLE_HOME_REGISTRY) {
  return (registry[role] || registry.sales).navId;
}

// ─── VIEW → NAV ID INDEX (highlight sidebar = turunan dari activeView) ─────────
const VIEW_NAV_INDEX = (() => {
  const idx = {};
  const reg = (view, navId) => { (idx[view] = idx[view] || []).push(navId); };
  for (const entry of NAV_STRUCTURE) {
    const walk = (item) => {
      if (item.hub) {
        (HUB_TABS[item.hub] || []).forEach((t) => reg(t.view, item.id));
      } else {
        reg(item.view || item.id, item.id);
      }
    };
    if (entry.type === "standalone") walk(entry);
    else (entry.items || []).forEach(walk);
  }
  return idx;
})();

export function resolveActiveNavId(activeView, currentNavId, role) {
  const candidates = VIEW_NAV_INDEX[activeView];
  if (currentNavId && candidates && candidates.includes(currentNavId)) return currentNavId;
  if (candidates && candidates.length) return candidates[0];
  const home = ROLE_HOME_REGISTRY[role];
  if (home && home.view === activeView) return home.navId;
  return currentNavId || "home";
}

// Smart guidance CTA.
export const GUIDANCE_MAP = {
  admin:                { label: "Audit",       target: "admin" },
  sales:                { label: "Cari Produk", target: "sales" },
  orders:               { label: "Review",      target: "orders" },
  purchasing:           { label: "Buat PO",     target: "purchasing" },
  operations:           { label: "WMS",         target: "operations" },
  "inventory-board":    { label: "Cek ATP",     target: "inventory-board" },
  "interco-transfers":  { label: "Approve",     target: "interco-transfers" },
  escalations:          { label: "Resolve",     target: "escalations" },
  documents:            { label: "Print",       target: "documents" },
};
