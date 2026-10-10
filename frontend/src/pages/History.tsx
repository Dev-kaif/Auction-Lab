import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Download, Eye, Trash2 } from "lucide-react";
import { ApiError, deleteExperiment, experimentCsvUrl, getExperiment, getExperiments } from "../api/client";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import type { ExperimentDetail, ExperimentSummary } from "../types/auction";

const dateText = (iso: string) => new Date(iso).toLocaleString();
const mechanismText = (value: string) => value === "both" ? "First-price + Second-price" : value.split(",").map((name) => ({ first_price: "First-price", second_price: "Second-price", gsp: "GSP", vcg: "VCG" } as Record<string, string>)[name] ?? name).join(" + ");
const typeText = (value: ExperimentSummary["experiment_type"]) => value === "manual_auction" ? "Manual auction" : "Automatic simulation";
const metricText = (metrics: Record<string, unknown>) => {
  if (metrics.n_auctions !== undefined) return `${Number(metrics.n_auctions).toLocaleString()} auctions · seed ${String(metrics.seed)} · ${Array.isArray(metrics.mean_revenue) ? `${metrics.mean_revenue.map((x) => `₹${Number(x).toFixed(2)}`).join(" / ")} mean revenue` : "aggregate results"}`;
  return `Winner ${String(metrics.winner ?? "—")} · revenue ₹${Number(metrics.revenue ?? 0).toFixed(2)} · winner payoff ₹${Number(metrics.winner_payoff ?? 0).toFixed(2)}`;
};

export default function History({ onClose }: { onClose?: () => void } = {}) {
  const [filter, setFilter] = useState<"all" | ExperimentSummary["experiment_type"]>("all");
  const [sort, setSort] = useState<"desc" | "asc">("desc");
  const [items, setItems] = useState<ExperimentSummary[]>([]); const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true); const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ExperimentDetail | null>(null); const [detailLoading, setDetailLoading] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<ExperimentSummary | null>(null); const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { const response = await getExperiments({ type: filter === "all" ? undefined : filter, sort }); setItems(response.items); setTotal(response.total); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Could not load experiment history."); }
    finally { setLoading(false); }
  }, [filter, sort]);
  useEffect(() => { void load(); }, [load]);

  const openDetails = async (item: ExperimentSummary) => {
    setSelected(null); setDetailLoading(true); setError(null);
    try { setSelected(await getExperiment(item.id)); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Could not load experiment details."); }
    finally { setDetailLoading(false); }
  };
  const confirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true); setError(null);
    try {
      await deleteExperiment(pendingDelete.id);
      if (selected?.id === pendingDelete.id) setSelected(null);
      setPendingDelete(null); await load();
    } catch (e) { setError(e instanceof ApiError ? e.message : "Could not delete this experiment."); }
    finally { setDeleting(false); }
  };

  return <div className="mx-auto max-w-6xl space-y-5">
    <header className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[.14em] text-indigo-700">Saved work</p><h1 className="mt-1 text-2xl font-semibold tracking-tight text-[#182440]">Experiment history</h1><p className="mt-1 text-sm text-slate-600">Reopen results, review settings, and export records.</p></div>{onClose && <Button variant="outline" className="min-h-10 rounded-lg" onClick={onClose}>Close</Button>}</header>
    <section className="space-y-4 rounded-2xl border border-[#e4e3df] bg-white p-4 shadow-[0_5px_20px_rgba(27,38,63,.035)] sm:p-5" aria-label="Saved experiments">
      <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-semibold text-[#1c2944]">Saved experiments <span className="ml-2 text-sm font-normal text-slate-500">{total} total</span></h2>
      <div className="flex flex-wrap gap-3">
        <label className="text-xs font-medium text-slate-600">Experiment type<select aria-label="Filter experiment type" className="mt-1 block min-h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-[#17233e] sm:w-auto" value={filter} onChange={(e) => setFilter(e.target.value as typeof filter)}><option value="all">All types</option><option value="manual_auction">Manual auction</option><option value="automatic_simulation">Automatic simulation</option></select></label>
        <label className="text-xs font-medium text-slate-600">Sort by date<select aria-label="Sort by date" className="mt-1 block min-h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-[#17233e] sm:w-auto" value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}><option value="desc">Newest first</option><option value="asc">Oldest first</option></select></label>
      </div></div>
      {loading && <p role="status" className="py-5 text-sm text-navy-600">Loading saved experiments…</p>}
      {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {!loading && !error && items.length === 0 && <p className="rounded-md bg-slate-50 px-4 py-6 text-sm text-navy-600">No saved experiments match this view. Run a manual auction or automatic simulation to create history.</p>}
      {!loading && items.length > 0 && <ul className="space-y-3">{items.map((item) => <li key={item.id} className="rounded-xl border border-slate-200 bg-[#fdfdfc] p-4 transition-shadow hover:shadow-sm"><div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"><div className="min-w-0 space-y-2"><div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-800">{typeText(item.experiment_type)}</span><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">{mechanismText(item.mechanism)}</span><time className="text-xs text-slate-500">{dateText(item.created_at)}</time></div><p className="break-words text-sm font-medium leading-5 text-[#263550]">{item.strategy}</p><p className="text-sm leading-5 text-slate-600">{metricText(item.metrics)}</p></div><div className="flex flex-wrap items-center gap-2 lg:shrink-0"><Button className="min-h-10 rounded-lg" variant="outline" onClick={() => void openDetails(item)} aria-label={`View details for ${item.id}`}><Eye className="h-4 w-4" aria-hidden />Details</Button><a className="inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm font-medium text-indigo-800 transition-colors hover:bg-indigo-50" href={experimentCsvUrl(item.id)} download aria-label={`Download CSV for ${item.id}`}><Download className="h-4 w-4" aria-hidden />CSV</a><Button className="min-h-10 rounded-lg text-red-700" variant="ghost" onClick={() => setPendingDelete(item)} aria-label={`Delete ${item.id}`}><Trash2 className="h-4 w-4" aria-hidden />Delete</Button></div></div></li>)}</ul>}
    </section>

    {detailLoading && <Card><CardContent role="status" className="text-sm text-navy-600">Loading experiment details…</CardContent></Card>}
    {selected && <Card><CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><CardTitle>Experiment details</CardTitle><a href={experimentCsvUrl(selected.id)} download className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:bg-slate-50"><Download className="h-4 w-4" aria-hidden />Download CSV</a></div></CardHeader><CardContent className="space-y-4 text-sm">
      <dl className="grid gap-3 sm:grid-cols-2"><div><dt className="font-medium">ID</dt><dd className="break-all font-mono text-xs">{selected.id}</dd></div><div><dt className="font-medium">Created</dt><dd>{dateText(selected.created_at)}</dd></div><div><dt className="font-medium">Type and mechanism</dt><dd>{typeText(selected.experiment_type)} · {mechanismText(selected.mechanism)}</dd></div><div><dt className="font-medium">Strategy</dt><dd>{selected.strategy}</dd></div></dl>
      <div className="grid gap-4 md:grid-cols-2"><section><h3 className="mb-1 font-semibold">Configuration</h3><pre className="max-h-80 overflow-auto rounded bg-slate-50 p-3 text-xs">{JSON.stringify(selected.configuration, null, 2)}</pre></section><section><h3 className="mb-1 font-semibold">Saved results and metrics</h3><pre className="max-h-80 overflow-auto rounded bg-slate-50 p-3 text-xs">{JSON.stringify(selected.result, null, 2)}</pre></section></div>
    </CardContent></Card>}

    {pendingDelete && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="presentation"><section role="alertdialog" aria-modal="true" aria-labelledby="delete-title" aria-describedby="delete-description" className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl"><div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 h-5 w-5 text-amber-600" aria-hidden /><div><h2 id="delete-title" className="font-semibold">Delete saved experiment?</h2><p id="delete-description" className="mt-1 text-sm text-navy-600">This will permanently remove the {typeText(pendingDelete.experiment_type).toLowerCase()} dated {dateText(pendingDelete.created_at)}.</p></div></div><div className="mt-5 flex justify-end gap-2"><Button variant="outline" disabled={deleting} onClick={() => setPendingDelete(null)}>Cancel</Button><Button className="bg-red-600 hover:bg-red-700" disabled={deleting} onClick={() => void confirmDelete()}>{deleting ? "Deleting…" : "Delete experiment"}</Button></div></section></div>}
  </div>;
}
