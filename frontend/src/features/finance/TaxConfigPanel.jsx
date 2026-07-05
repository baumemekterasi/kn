/**
 * TaxConfigPanel (EPIC 7) — Konfigurasi Pajak per SCOPE (Global / Entitas).
 * CONFIGURABLE tax-plan: tarif PPN, mode, e-Faktur, + butir PPh (tambah/ubah/hapus).
 * Simpan via PUT /api/settings {scope, tax:{...}}. Non-PKP: PPN dipaksa 0 oleh backend
 * (mengikuti default_tax_mode entitas) — panel menampilkan catatan tsb.
 * Edit hanya utk admin/manager (permission accounting.manage).
 */
import { useEffect, useMemo, useState } from "react";
import { Save, Plus, Trash2, Settings, ShieldAlert, Info } from "lucide-react";
import KNSelect from "../../components/KNSelect";
import ErrorNotice from "../../components/ErrorNotice";
import axios, { API } from "../../services/apiClient";

const PPN_MODES = [
  { value: "excluded", label: "Excluded (PPN ditambahkan)" },
  { value: "included", label: "Included (harga sudah termasuk PPN)" },
];
const BASIS_OPTS = [
  { value: "payroll", label: "Payroll (PPh21 otomatis/TER)" },
  { value: "omzet", label: "Omzet (rate% × peredaran bruto)" },
  { value: "manual", label: "Manual (rekam DPP)" },
];

export default function TaxConfigPanel({ currentUser, selectedEntity, entity, onSaved }) {
  const canManage = ["admin", "manager"].includes(currentUser?.role);
  const entSpecific = selectedEntity && selectedEntity !== "all";
  const [scope, setScope] = useState("global");
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  const scopeOpts = useMemo(() => {
    const opts = [{ value: "global", label: "Global (default semua entitas)" }];
    if (entSpecific) opts.push({ value: selectedEntity, label: `${entity?.name || selectedEntity} (khusus)` });
    return opts;
  }, [entSpecific, selectedEntity, entity]);

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true); setOk(""); setError("");
      try {
        // scope=global → baca /settings (global tersimpan); scope=entity → baca effective utk entitas
        const res = scope === "global"
          ? await axios.get(`${API}/settings`)
          : await axios.get(`${API}/settings/effective`, { params: { entity_id: scope } });
        const tax = (res.data?.tax) || {};
        if (!alive) return;
        setForm({
          ppn_rate: tax.ppn_rate ?? 12,
          dpp_nilai_lain: !!tax.dpp_nilai_lain,
          ppn_mode: tax.ppn_mode || "excluded",
          efaktur_enabled: tax.efaktur_enabled ?? true,
          is_pkp: tax.is_pkp ?? true,
          pph_items: Array.isArray(tax.pph_items) ? tax.pph_items.map((x) => ({ ...x })) : [],
        });
      } catch (e) {
        if (alive) setError(e.response?.data?.detail || "Gagal memuat konfigurasi pajak.");
      } finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [scope]);

  const nonPkpScope = scope !== "global" && form && form.is_pkp === false;

  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const setItem = (i, k, v) => setForm((f) => {
    const items = f.pph_items.map((it, idx) => (idx === i ? { ...it, [k]: v } : it));
    return { ...f, pph_items: items };
  });
  const addItem = () => setForm((f) => ({
    ...f,
    pph_items: [...f.pph_items, { code: `pph_${f.pph_items.length + 1}`, name: "Butir PPh Baru", rate: 0, basis: "manual", enabled: true }],
  }));
  const removeItem = (i) => setForm((f) => ({ ...f, pph_items: f.pph_items.filter((_, idx) => idx !== i) }));

  const save = async () => {
    setSaving(true); setError(""); setOk("");
    try {
      const tax = {
        ppn_rate: parseFloat(form.ppn_rate) || 0,
        dpp_nilai_lain: !!form.dpp_nilai_lain,
        ppn_mode: form.ppn_mode,
        efaktur_enabled: !!form.efaktur_enabled,
        pph_items: form.pph_items.map((it) => ({
          code: (it.code || "").trim(), name: (it.name || "").trim(),
          rate: parseFloat(it.rate) || 0, basis: it.basis || "manual", enabled: !!it.enabled,
        })),
      };
      await axios.put(`${API}/settings`, { scope, tax });
      setOk(scope === "global" ? "Konfigurasi global tersimpan." : "Override entitas tersimpan.");
      onSaved && onSaved();
    } catch (e) {
      setError(e.response?.data?.detail || "Gagal menyimpan konfigurasi.");
    } finally { setSaving(false); }
  };

  return (
    <div data-testid="tax-config-panel">
      <div className="section-card">
        <div className="section-head">
          <div className="flex items-center gap-2"><Settings size={15} className="text-[#6B219A]" /><h3 className="text-[12px] font-bold">Konfigurasi Pajak</h3></div>
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-[10px] font-bold uppercase text-[#8E8E93]">Cakupan</span>
            <KNSelect data-testid="tax-config-scope" value={scope} onValueChange={setScope}
              options={scopeOpts} className="field !py-1 !px-2 text-[12px] w-auto" />
          </div>
        </div>
        <div className="section-body">
          <ErrorNotice message={error} onDismiss={() => setError("")} testId="tax-config-error" />
          {loading || !form ? (
            <div className="grid gap-2" data-testid="tax-config-loading">{[0, 1, 2].map((i) => <div key={i} className="h-10 bg-[#F5F5F7] rounded animate-pulse" />)}</div>
          ) : (
            <>
              {/* PPN section */}
              <div className="rounded-lg border border-[#EFF0F2] p-3 mb-3">
                <p className="text-[11px] font-bold uppercase text-[#6B6B73] mb-2">PPN</p>
                {nonPkpScope && (
                  <div className="flex items-start gap-2 rounded-md bg-[#FDF3E7] px-3 py-2 mb-3 text-[11px] text-[#B45309]" data-testid="tax-config-nonpkp">
                    <ShieldAlert size={14} className="mt-0.5 shrink-0" />
                    <span><b>{entity?.name}</b> berstatus <b>Non-PKP</b>. Backend otomatis memaksa tarif PPN = 0 &amp; menonaktifkan e-Faktur untuk entitas ini, apa pun nilai yang disimpan.</span>
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <label className="grid gap-1">
                    <span className="text-[11px] font-semibold text-[#3C3C43]">Tarif PPN (%)</span>
                    <input data-testid="tax-config-ppn-rate" type="number" min="0" step="0.1" className="field" value={form.ppn_rate}
                      disabled={!canManage} onChange={(e) => setField("ppn_rate", e.target.value)} />
                  </label>
                  <label className="grid gap-1">
                    <span className="text-[11px] font-semibold text-[#3C3C43]">Mode PPN</span>
                    <KNSelect data-testid="tax-config-ppn-mode" value={form.ppn_mode} onValueChange={(v) => setField("ppn_mode", v)}
                      options={PPN_MODES} className="field" disabled={!canManage} />
                  </label>
                  <label className="flex items-center gap-2 mt-5">
                    <input data-testid="tax-config-efaktur" type="checkbox" checked={!!form.efaktur_enabled}
                      disabled={!canManage} onChange={(e) => setField("efaktur_enabled", e.target.checked)} />
                    <span className="text-[12px] text-[#3C3C43]">Terbitkan e-Faktur (PKP)</span>
                  </label>
                </div>
                <label className="flex items-start gap-2 mt-3" data-testid="tax-config-dpp-nilai-lain-row">
                  <input data-testid="tax-config-dpp-nilai-lain" type="checkbox" className="mt-0.5" checked={!!form.dpp_nilai_lain}
                    disabled={!canManage} onChange={(e) => setField("dpp_nilai_lain", e.target.checked)} />
                  <span className="text-[12px] text-[#3C3C43]">
                    <b>DPP Nilai Lain 11/12</b> (PMK 131/2024 — Coretax). DPP = 11/12 × harga jual, kode transaksi Faktur 04.
                    PPN efektif = <b>{(((parseFloat(form.ppn_rate) || 0) * 11) / 12).toFixed(2)}%</b> dari harga jual.
                    Nonaktifkan untuk barang mewah (tarif {form.ppn_rate || 0}% penuh).
                  </span>
                </label>
              </div>

              {/* PPh items */}
              <div className="rounded-lg border border-[#EFF0F2] p-3">
                <div className="flex items-center gap-2 mb-2">
                  <p className="text-[11px] font-bold uppercase text-[#6B6B73]">Butir PPh (fleksibel per tax-plan)</p>
                  {canManage && (
                    <button data-testid="tax-config-add-pph" className="ml-auto inline-flex items-center gap-1 text-[11px] font-semibold text-[#0058CC] hover:underline" onClick={addItem}>
                      <Plus size={12} /> Tambah butir
                    </button>
                  )}
                </div>
                {form.pph_items.length === 0 ? (
                  <p className="text-[11px] text-[#8E8E93] py-3 text-center" data-testid="tax-config-pph-empty">Belum ada butir PPh. Tambah untuk mulai.</p>
                ) : (
                  <div className="grid gap-2" data-testid="tax-config-pph-list">
                    {form.pph_items.map((it, i) => (
                      <div key={i} data-testid={`tax-config-pph-${i}`} className="grid grid-cols-12 gap-2 items-center rounded-md border border-[#F0F0F2] bg-[#FCFCFD] px-2 py-2">
                        <input type="checkbox" className="col-span-1 justify-self-center" checked={!!it.enabled} disabled={!canManage}
                          data-testid={`tax-config-pph-enabled-${i}`} onChange={(e) => setItem(i, "enabled", e.target.checked)} />
                        <input className="field col-span-4 !py-1 text-[12px]" value={it.name} disabled={!canManage}
                          data-testid={`tax-config-pph-name-${i}`} onChange={(e) => setItem(i, "name", e.target.value)} placeholder="Nama butir" />
                        <div className="col-span-4">
                          <KNSelect value={it.basis} onValueChange={(v) => setItem(i, "basis", v)} options={BASIS_OPTS}
                            className="field !py-1 text-[12px]" disabled={!canManage} data-testid={`tax-config-pph-basis-${i}`} />
                        </div>
                        <div className="col-span-2 flex items-center gap-1">
                          <input type="number" min="0" step="0.1" className="field !py-1 text-[12px] w-full" value={it.rate}
                            disabled={!canManage || it.basis === "payroll"} data-testid={`tax-config-pph-rate-${i}`}
                            onChange={(e) => setItem(i, "rate", e.target.value)} />
                          <span className="text-[11px] text-[#9A9BA3]">%</span>
                        </div>
                        {canManage ? (
                          <button data-testid={`tax-config-pph-del-${i}`} className="col-span-1 icon-button !w-6 !h-6 justify-self-center" onClick={() => removeItem(i)} aria-label="Hapus butir">
                            <Trash2 size={12} className="text-[#C0392B]" />
                          </button>
                        ) : <span className="col-span-1" />}
                      </div>
                    ))}
                  </div>
                )}
                <p className="text-[10px] text-[#9A9BA3] mt-2 flex items-center gap-1"><Info size={11} /> Basis <b>payroll</b> memakai PPh21 aktual (TER) — tarif diabaikan. <b>omzet</b>/<b>manual</b> = tarif × DPP.</p>
              </div>

              {ok && <p className="text-[11px] text-[#1B7F4B] mt-3" data-testid="tax-config-ok">{ok}</p>}
              {canManage && (
                <div className="flex items-center justify-end mt-3">
                  <button data-testid="tax-config-save" className="primary-button inline-flex items-center gap-1.5" disabled={saving} onClick={save}>
                    <Save size={13} /> {saving ? "Menyimpan…" : `Simpan (${scope === "global" ? "Global" : "Entitas"})`}
                  </button>
                </div>
              )}
              {!canManage && <p className="text-[11px] text-[#8E8E93] mt-3">Anda hanya dapat melihat konfigurasi (butuh izin accounting.manage untuk mengubah).</p>}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
