import { useEffect, useState } from "react";
import axios, { API } from "../../services/apiClient";
import { Settings2, Save, RefreshCw } from "lucide-react";
import KNSelect from "../../components/KNSelect";
import ErrorNotice from "../../components/ErrorNotice";

function NumField({ label, value, onChange, suffix, testId }) {
  return (
    <div>
      <label className="block text-[10.5px] font-semibold text-[#6B6B73] mb-1">{label}</label>
      <div className="flex items-center gap-1">
        <input data-testid={testId} type="number" step="0.01" value={value} onChange={(e) => onChange(e.target.value)} className="field tabular-nums" />
        {suffix && <span className="text-[11px] text-[#6B6B73]">{suffix}</span>}
      </div>
    </div>
  );
}

export default function PayrollSetupView({ currentUser }) {
  const [cfg, setCfg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => { load(); }, []);
  async function load() {
    setLoading(true);
    try { const r = await axios.get(`${API}/hr/payroll/settings`); setCfg(r.data || {}); setError(""); }
    catch (e) { setError(e.response?.data?.detail || "Gagal memuat konfigurasi."); }
    finally { setLoading(false); }
  }
  function setBpjs(k, v) { setCfg((c) => ({ ...c, bpjs: { ...(c.bpjs || {}), [k]: parseFloat(v) || 0 } })); }
  function setOt(k, v) { setCfg((c) => ({ ...c, overtime: { ...(c.overtime || {}), [k]: parseFloat(v) || 0 } })); }
  async function save() {
    setSaving(true);
    try {
      const body = { settings: { bpjs: cfg.bpjs, overtime: cfg.overtime, ter_enabled: cfg.ter_enabled, payroll_commission_mode: cfg.payroll_commission_mode } };
      const r = await axios.put(`${API}/hr/payroll/settings`, body);
      setCfg(r.data || cfg); setNotice("Konfigurasi tersimpan."); setError("");
    } catch (e) { setError(e.response?.data?.detail || "Gagal menyimpan."); }
    finally { setSaving(false); }
  }

  if (loading) return <div className="section-card py-12 text-center text-[12px] text-[#6B6B73]" data-testid="payroll-setup-loading">Memuat konfigurasi...</div>;
  if (!cfg) return <ErrorNotice message={error || "Konfigurasi tidak tersedia."} onRetry={load} testId="payroll-setup-error" />;
  const b = cfg.bpjs || {};
  const modeOpts = [{ value: "accrue_then_settle", label: "Accrue → Settle (default, anti double-count)" }, { value: "expense_in_payroll", label: "Beban langsung di payroll" }];

  return (
    <div data-testid="payroll-setup-view">
      {notice && (<div className="notice-bar success" data-testid="payroll-setup-notice"><span>{notice}</span><button onClick={() => setNotice("")}>×</button></div>)}
      <ErrorNotice message={error} onRetry={load} onDismiss={() => setError("")} testId="payroll-setup-error" />

      <div className="section-card mb-3">
        <div className="section-head"><div className="flex items-center gap-2"><Settings2 size={16} className="text-[#0058CC]" /><h2 data-testid="payroll-setup-title">Setup Gaji, BPJS & PPh21</h2></div>
          <div className="flex items-center gap-2">
            <button onClick={load} className="icon-button" title="Muat ulang"><RefreshCw size={15} /></button>
            <button data-testid="payroll-setup-save" disabled={saving} onClick={save} className="primary-button !py-1.5"><Save size={13} /> {saving ? "Menyimpan..." : "Simpan"}</button>
          </div>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="section-card">
          <div className="section-head"><h2 className="text-[13px] font-bold">Iuran BPJS (persen)</h2></div>
          <div className="section-body grid grid-cols-2 gap-2">
            <NumField label="Kesehatan — Karyawan" value={b.kes_rate_employee} onChange={(v) => setBpjs("kes_rate_employee", v)} suffix="%" testId="cfg-kes-emp" />
            <NumField label="Kesehatan — Perusahaan" value={b.kes_rate_employer} onChange={(v) => setBpjs("kes_rate_employer", v)} suffix="%" testId="cfg-kes-er" />
            <NumField label="JHT — Karyawan" value={b.jht_rate_employee} onChange={(v) => setBpjs("jht_rate_employee", v)} suffix="%" testId="cfg-jht-emp" />
            <NumField label="JHT — Perusahaan" value={b.jht_rate_employer} onChange={(v) => setBpjs("jht_rate_employer", v)} suffix="%" testId="cfg-jht-er" />
            <NumField label="JP — Karyawan" value={b.jp_rate_employee} onChange={(v) => setBpjs("jp_rate_employee", v)} suffix="%" testId="cfg-jp-emp" />
            <NumField label="JP — Perusahaan" value={b.jp_rate_employer} onChange={(v) => setBpjs("jp_rate_employer", v)} suffix="%" testId="cfg-jp-er" />
            <NumField label="JKM — Perusahaan" value={b.jkm_rate_employer} onChange={(v) => setBpjs("jkm_rate_employer", v)} suffix="%" testId="cfg-jkm-er" />
          </div>
        </div>

        <div className="space-y-3">
          <div className="section-card">
            <div className="section-head"><h2 className="text-[13px] font-bold">Lembur & Pajak</h2></div>
            <div className="section-body grid grid-cols-2 gap-2">
              <NumField label="Pengali Lembur" value={cfg.overtime?.multiplier} onChange={(v) => setOt("multiplier", v)} suffix="x" testId="cfg-ot-mult" />
              <NumField label="Pembagi Jam/Bln" value={cfg.overtime?.hours_divisor} onChange={(v) => setOt("hours_divisor", v)} testId="cfg-ot-div" />
              <div>
                <label className="block text-[10.5px] font-semibold text-[#6B6B73] mb-1">PPh21 TER aktif</label>
                <KNSelect data-testid="cfg-ter-enabled" value={cfg.ter_enabled ? "on" : "off"} onValueChange={(v) => setCfg((c) => ({ ...c, ter_enabled: v === "on" }))} className="field" options={[{ value: "on", label: "Ya (PMK 168/2023)" }, { value: "off", label: "Nonaktif" }]} />
              </div>
            </div>
          </div>
          <div className="section-card">
            <div className="section-head"><h2 className="text-[13px] font-bold">Integrasi Komisi → Payroll</h2></div>
            <div className="section-body">
              <KNSelect data-testid="cfg-commission-mode" value={cfg.payroll_commission_mode || "accrue_then_settle"} onValueChange={(v) => setCfg((c) => ({ ...c, payroll_commission_mode: v }))} className="field" options={modeOpts} />
              <p className="text-[10.5px] text-[#6B6B73] mt-2">Accrue→Settle: komisi sudah jadi beban saat akrual penjualan; payroll memindah hutang 2-1500 → 2-1600 (anti dobel beban).</p>
            </div>
          </div>
        </div>
      </div>

      <div className="section-card mt-3">
        <div className="section-head"><h2 className="text-[13px] font-bold">PTKP (read-only)</h2></div>
        <div className="section-body grid grid-cols-2 md:grid-cols-4 gap-2">
          {Object.entries(cfg.ptkp_table || {}).map(([k, v]) => (
            <div key={k} className="rounded-lg border border-[#EFF0F2] px-2 py-1.5"><p className="text-[10px] text-[#6B6B73]">{k}</p><p className="text-[12px] font-semibold tabular-nums">{Number(v).toLocaleString("id-ID")}</p></div>
          ))}
        </div>
      </div>
    </div>
  );
}
