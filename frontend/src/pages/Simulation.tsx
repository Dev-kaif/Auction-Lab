import { useEffect, useState } from "react";
import { Loader2, Play, RotateCcw } from "lucide-react";
import { ApiError, runSimulation } from "../api/client";
import SimulationResults from "../components/auction/SimulationResults";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { useSimulation } from "../hooks/SimulationContext";
import { ADVERTISER_IDS, N_OPTIONS, buildRequest, defaultForm, parseAlpha, type SimForm } from "../lib/simulation";
import type { MechanismChoice } from "../types/simulation";

const selectCls = "min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-[#17233e] focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100 disabled:bg-slate-100";
const inputCls = "min-h-11 w-full rounded-lg border-slate-300 bg-white text-base";

export default function Simulation({ mechanism: sharedMechanism, onMechanismChange, compact = false }: { mechanism?: MechanismChoice; onMechanismChange?: (mechanism: Exclude<MechanismChoice, "both" | "all">) => void; compact?: boolean } = {}) {
  const { form, setForm, result, setResult } = useSimulation();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (sharedMechanism && form.mechanism !== sharedMechanism) {
      setForm({ ...form, mechanism: sharedMechanism });
      setResult(null);
    }
  }, [sharedMechanism]);

  const set = <K extends keyof SimForm>(k: K, v: SimForm[K]) => {
    setForm({ ...form, [k]: v });
    setResult(null);
    setErrors((e) => { const n = { ...e }; delete n[k as string]; if (k === "fixed") Object.keys(n).forEach((x) => x.startsWith("fixed") && delete n[x]); return n; });
  };
  const run = async (f: SimForm) => {
    const built = buildRequest(f);
    setApiError(null);
    if (!built.ok) { setErrors(built.errors); return; }
    setErrors({}); setResult(null); setRunning(true);
    try { setResult(await runSimulation(built.request)); }
    catch (e) { setApiError(e instanceof ApiError ? e.message : "Unexpected error while running the simulation."); }
    finally { setRunning(false); }
  };
  const rerun = (seed: number) => { const f = { ...form, seed: String(seed) }; setForm(f); void run(f); };
  const reset = () => { setForm(defaultForm()); setErrors({}); setApiError(null); setResult(null); };
  const err = (k: string) => errors[k] && <p id={`${k}-err`} className="mt-1 text-sm text-red-700">{errors[k]}</p>;
  const text = (k: keyof SimForm & ("low" | "high" | "seed" | "customAlpha" | "deviatorAlpha"), label: string, hint?: string) => (
    <div>
      <label htmlFor={k} className="mb-1.5 block text-sm font-medium text-[#283550]">{label}</label>
      <Input id={k} className={inputCls} inputMode="decimal" value={form[k]} disabled={running} aria-invalid={!!errors[k]} aria-describedby={errors[k] ? `${k}-err` : undefined} onChange={(e) => set(k, e.target.value)} />
      {hint && !errors[k] && <p className="mt-1.5 text-xs leading-5 text-slate-500">{hint}</p>}{err(k)}
    </div>
  );
  const check = (k: "useTruthful" | "use80" | "use75" | "useCustom" | "useDeviator", title: string, subtitle: string) => (
    <label className="flex min-h-[68px] cursor-pointer items-start gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 transition-colors hover:border-indigo-300 has-[:checked]:border-indigo-400 has-[:checked]:bg-indigo-50/50">
      <input className="mt-1 h-4 w-4 accent-indigo-700" type="checkbox" checked={form[k]} disabled={running} onChange={(e) => set(k, e.target.checked)} />
      <span><span className="block text-sm font-medium text-[#1c2944]">{title}</span><span className="mt-0.5 block text-xs leading-5 text-slate-500">{subtitle}</span></span>
    </label>
  );
  const customA = form.useCustom ? parseAlpha(form.customAlpha) : null;
  const devA = form.useDeviator ? parseAlpha(form.deviatorAlpha) : null;
  const overbidWarn = (customA?.ok && customA.value > 1) || (devA?.ok && devA.value > 1);

  return <div className={`mx-auto ${compact ? "max-w-none space-y-7" : "max-w-5xl space-y-7"}`}>
    {!compact && <header><p className="text-sm font-semibold uppercase tracking-[0.13em] text-indigo-700">Automatic experiment</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-[#15213b]">Configure, run, compare</h1><p className="mt-2 max-w-2xl leading-6 text-slate-600">Compare auction outcomes across repeated valuation scenarios. The backend uses the same generated scenarios for each strategy and mechanism.</p></header>}

    <section aria-label="Simulation settings" className="overflow-hidden rounded-2xl border border-[#e4e3df] bg-white shadow-[0_8px_26px_rgba(27,38,63,.045)]">
      <div className="border-b border-[#eeede9] px-5 py-5 sm:px-7">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-700">01 · Configure the experiment</p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight text-[#182440]">Simulation settings</h2>
        <p className="mt-1 text-sm text-slate-500">Set the auction scale, valuation environment, and bidding rules to compare.</p>
      </div>
      <div className="space-y-7 px-5 py-6 sm:px-7">
        <div className="grid gap-5 sm:grid-cols-2">
          <div><label htmlFor="n" className="mb-1.5 block text-sm font-medium text-[#283550]">Auctions per experiment</label><select id="n" className={selectCls} value={form.n} disabled={running} onChange={(e) => set("n", Number(e.target.value))}>{N_OPTIONS.map((n) => <option key={n} value={n}>{n.toLocaleString("en-IN")} auctions</option>)}</select><p className="mt-1.5 text-xs text-slate-500">Each selected mechanism × strategy combination runs this many auctions.</p></div>
          <div><label htmlFor="mechanism" className="mb-1.5 block text-sm font-medium text-[#283550]">Mechanisms</label><select id="mechanism" className={selectCls} value={form.mechanism} disabled={running} onChange={(e) => { const value = e.target.value as MechanismChoice; set("mechanism", value); if (value !== "both" && value !== "all") onMechanismChange?.(value); }}><option value="both">Compare first-price and second-price</option><option value="all">Compare all four mechanisms</option><option value="first_price">First-price only</option><option value="second_price">Second-price only</option><option value="gsp">GSP only</option><option value="vcg">VCG only</option></select></div>
        </div>

        <fieldset className="border-t border-[#eeede9] pt-5" disabled={running} aria-label="Simulation slot click-through rates"><legend className="text-sm font-semibold text-[#1c2944]">Slot click-through rates</legend><p className="mt-1 text-xs text-slate-500">Used by GSP and VCG; values are position CTR probabilities in non-increasing order.</p><div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">{form.clickThroughRates.map((rate, i) => <label key={i} className="text-xs font-medium text-slate-600">Slot {i + 1}<Input className={`${inputCls} mt-1`} inputMode="decimal" value={rate} aria-invalid={!!errors[`ctr${i}`]} onChange={(e) => set("clickThroughRates", form.clickThroughRates.map((x, j) => i === j ? e.target.value : x))} aria-label={`Slot ${i + 1} click-through rate`} />{err(`ctr${i}`)}</label>)}</div><div className="mt-3 flex items-center gap-2"><label htmlFor="slot-count" className="text-xs text-slate-600">Number of slots</label><select id="slot-count" className="min-h-9 rounded-lg border border-slate-300 bg-white px-2 text-sm" value={form.clickThroughRates.length} onChange={(e) => set("clickThroughRates", Array.from({ length: Number(e.target.value) }, (_, i) => form.clickThroughRates[i] ?? ["1", "0.7", "0.4", "0.2"][i]))}>{[1,2,3,4].map((n) => <option key={n} value={n}>{n}</option>)}</select></div>{err("clickThroughRates")}</fieldset>

        <fieldset disabled={running} className="border-t border-[#eeede9] pt-6">
          <legend className="mb-3 text-base font-semibold text-[#1c2944]">Valuation environment</legend>
          <div className="mb-4 inline-flex rounded-xl bg-[#f2f3f7] p-1" role="group" aria-label="Valuation generation">
            {(["random", "fixed"] as const).map((m) => <button key={m} type="button" aria-pressed={form.valMode === m} onClick={() => set("valMode", m)} className={`min-h-10 rounded-lg px-4 text-sm font-medium transition-colors ${form.valMode === m ? "bg-white text-indigo-800 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}>{m === "random" ? "Random values" : "Fixed values"}</button>)}
          </div>
          {form.valMode === "random" ? <div className="grid max-w-xl gap-4 sm:grid-cols-2">{text("low", "Lower bound (₹)")}{text("high", "Upper bound (₹)")}</div> : <div className="space-y-3"><div className="grid gap-3 grid-cols-2 sm:grid-cols-4">{ADVERTISER_IDS.map((id, i) => <div key={id}><label htmlFor={`fixed-${id}`} className="mb-1.5 block text-sm font-medium text-[#283550]">Advertiser {id} (₹)</label><Input id={`fixed-${id}`} className={inputCls} inputMode="decimal" value={form.fixed[i]} aria-invalid={!!errors[`fixed${i}`]} onChange={(e) => set("fixed", form.fixed.map((x, j) => j === i ? e.target.value : x))} />{err(`fixed${i}`)}</div>)}</div><p className="text-sm leading-5 text-slate-500">A fixed scenario repeats in every auction; random seed has no effect on valuations.</p></div>}
        </fieldset>

        <fieldset disabled={running} className="border-t border-[#eeede9] pt-6">
          <legend className="text-base font-semibold text-[#1c2944]">Bidding strategies</legend><p className="mb-4 mt-1 text-sm text-slate-500">Bid rule: bᵢ = αᵢvᵢ. Use matched profiles to compare mechanisms on the same valuations.</p>
          <div className="grid gap-3 sm:grid-cols-2">{check("useTruthful", "Truthful · α = 1", "Each advertiser bids their valuation.")}{check("use80", "Shaded · α = 0.8", "Each advertiser bids 80% of valuation.")}{check("use75", "Shaded · α = 0.75", "Each advertiser bids 75% of valuation.")}{check("useCustom", "Custom fixed fraction", "Apply one α value to all advertisers.")}</div>
          {form.useCustom && <div className="mt-4 max-w-sm">{text("customAlpha", "Custom α (0 to 1.5)", "Fractions above 1 represent overbidding.")}</div>}
          <div className="mt-4 rounded-xl border border-dashed border-slate-300 p-4"><div className="flex items-start gap-3"><input id="useDeviator" className="mt-1 h-4 w-4 accent-indigo-700" type="checkbox" checked={form.useDeviator} onChange={(e) => set("useDeviator", e.target.checked)} /><label htmlFor="useDeviator" className="text-sm font-medium text-[#1c2944]">Explore a unilateral deviation</label></div><p className="ml-7 mt-1 text-xs leading-5 text-slate-500">One advertiser changes their bid fraction while the other three bid truthfully.</p>{form.useDeviator && <div className="mt-4 grid gap-4 sm:grid-cols-2"><div><label htmlFor="deviator" className="mb-1.5 block text-sm font-medium text-[#283550]">Deviating advertiser</label><select id="deviator" className={selectCls} value={form.deviator} onChange={(e) => set("deviator", e.target.value as SimForm["deviator"])}>{ADVERTISER_IDS.map((id) => <option key={id} value={id}>{id}</option>)}</select></div>{text("deviatorAlpha", "Deviator α (0 to 1.5)")}</div>}</div>
          {overbidWarn && <p role="note" className="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm leading-5 text-amber-900">α above 1 means overbidding. An advertiser may win and pay more than their valuation, producing negative payoff.</p>}{err("profiles")}
        </fieldset>

        <details className="border-t border-[#eeede9] pt-5"><summary className="cursor-pointer text-sm font-semibold text-[#283550]">Advanced · random seed</summary><div className="mt-4 max-w-sm">{text("seed", "Random seed (optional)", "Leave blank to generate one. The seed returned by the API appears with results and can be rerun.")}</div></details>

        <div className="flex flex-col-reverse gap-3 border-t border-[#eeede9] pt-5 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-slate-500">Results appear below after the API completes.</p><div className="flex gap-3"><Button variant="outline" className="min-h-12 rounded-xl px-4" disabled={running} onClick={reset}><RotateCcw className="h-4 w-4" aria-hidden />Reset</Button><Button className="min-h-12 rounded-xl bg-indigo-700 px-6 text-base hover:bg-indigo-800" disabled={running} onClick={() => void run(form)}>{running ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> : <Play className="h-5 w-5" aria-hidden />}{running ? "Running simulation…" : "Run simulation"}</Button></div></div>
        {Object.keys(errors).length > 0 && <p role="alert" className="text-sm text-red-700">Fix the highlighted fields before running the simulation.</p>}{apiError && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{apiError}</p>}
      </div>
    </section>
    {running && <p className="flex items-center gap-2 text-sm text-indigo-800" role="status"><Loader2 className="h-4 w-4 animate-spin" aria-hidden />The simulation is running. Results will appear here.</p>}
    {result && <SimulationResults data={result} busy={running} onRerun={rerun} />}
    {!result && !running && <div className="rounded-2xl border border-dashed border-slate-300 px-5 py-8 text-center"><p className="text-sm font-medium text-[#34415e]">Your experiment results will appear here</p><p className="mt-1 text-sm text-slate-500">Choose a valuation environment and strategy, then run the simulation.</p></div>}
  </div>;
}
