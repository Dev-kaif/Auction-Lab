import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { Loader2, Play, RotateCcw } from "lucide-react";
import { ApiError, runAuction } from "../api/client";
import RevealResults, { type Stage } from "../components/auction/RevealResults";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { parseAmount } from "../lib/validation";
import type { AuctionOut, Mechanism } from "../types/auction";

const IDS = ["A", "B", "C", "D"] as const;
const DEFAULT_VALS = ["100", "80", "60", "40"];
const DEFAULT_CTRS = ["1", "0.7", "0.4"];
const STEP_MS = 650;
const SEQUENCE: Stage[] = ["ranking", "ranked", "winner", "price", "done"];

export default function ManualAuction({ mechanism: sharedMechanism, compact = false }: { mechanism?: Mechanism; onMechanismChange?: (mechanism: Mechanism) => void; compact?: boolean } = {}) {
  const reduce = useReducedMotion();
  const mechanism = sharedMechanism ?? "second_price";
  const [vals, setVals] = useState<string[]>(DEFAULT_VALS);
  const [bids, setBids] = useState<string[]>(DEFAULT_VALS);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<AuctionOut | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [fraction, setFraction] = useState("0.8");
  const [clickThroughRates, setClickThroughRates] = useState<string[]>(DEFAULT_CTRS);
  const timers = useRef<number[]>([]);

  useEffect(() => {
    if (sharedMechanism && result && result.mechanism !== sharedMechanism) {
      clearTimers();
      setResult(null);
      setStage("idle");
    }
  }, [sharedMechanism]);

  const clearTimers = () => { timers.current.forEach(window.clearTimeout); timers.current = []; };
  useEffect(() => clearTimers, []);

  const animating = result !== null && stage !== "done";
  const locked = running || animating;

  const setAt = (arr: string[], i: number, v: string) => arr.map((x, j) => (j === i ? v : x));
  const edit = (kind: "v" | "b", i: number, v: string) => {
    (kind === "v" ? setVals : setBids)((prev) => setAt(prev, i, v));
    setResult(null); setStage("idle"); clearTimers();
    setErrors((e) => { const n = { ...e }; delete n[`${kind}${i}`]; return n; });
  };

  const play = (r: AuctionOut) => {
    clearTimers();
    setResult(r);
    if (reduce) { setStage("done"); return; }
    SEQUENCE.forEach((s, k) => {
      timers.current.push(window.setTimeout(() => setStage(s), k * STEP_MS));
    });
  };

  const skip = () => { clearTimers(); setStage("done"); };

  const reset = () => {
    clearTimers(); setVals(DEFAULT_VALS); setBids(DEFAULT_VALS); setClickThroughRates(DEFAULT_CTRS); setErrors({}); setApiError(null);
    setResult(null); setStage("idle"); setRunning(false);
  };

  const truthfulOne = (i: number) => edit("b", i, vals[i]);
  const truthfulAll = () => { setBids([...vals]); setResult(null); setStage("idle"); setErrors((e) => Object.fromEntries(Object.entries(e).filter(([k]) => !k.startsWith("b")))); };
  const applyFraction = () => {
    const alpha = Number(fraction);
    if (!Number.isFinite(alpha) || alpha < 0 || alpha > 1.5) { setApiError("Enter a bidding fraction from 0 to 1.5."); return; }
    setApiError(null);
    setBids(vals.map((v, i) => {
      const p = parseAmount(v);
      return p.ok ? (Math.round(p.value * alpha * 100) / 100).toFixed(2).replace(/\.00$/, "") : bids[i];
    }));
    setResult(null); setStage("idle");
  };

  const onRun = async () => {
    const errs: Record<string, string> = {};
    const v: number[] = [], b: number[] = [];
    IDS.forEach((_, i) => {
      const pv = parseAmount(vals[i]); const pb = parseAmount(bids[i]);
      if (pv.ok) v.push(pv.value); else errs[`v${i}`] = pv.error;
      if (pb.ok) b.push(pb.value); else errs[`b${i}`] = pb.error;
    });
    setErrors(errs); setApiError(null);
    if (Object.keys(errs).length) return;

    if (mechanism === "gsp" || mechanism === "vcg") {
      const rates = clickThroughRates.map((rate) => Number(rate.trim()));
      const ratesAreValid = clickThroughRates.every((rate) => rate.trim() !== "")
        && rates.every((rate) => Number.isFinite(rate) && rate >= 0 && rate <= 1)
        && rates.every((rate, index) => index === 0 || rates[index - 1] >= rate);
      if (!ratesAreValid) {
        setApiError("Enter finite slot CTRs between 0 and 1 in non-increasing order.");
        return;
      }
    }

    setRunning(true); setResult(null); setStage("idle");
    try {
      play(await runAuction({ mechanism, valuations: v, bids: b, click_through_rates: clickThroughRates.map(Number) }));
    } catch (e) {
      setApiError(e instanceof ApiError ? e.message : "Unexpected error while running the auction.");
    } finally {
      setRunning(false);
    }
  };

  const field = (kind: "v" | "b", i: number) => {
    const id = `${kind}-${IDS[i]}`; const key = `${kind}${i}`; const err = errors[key];
    return (
      <div>
        <Input id={id} inputMode="decimal" value={(kind === "v" ? vals : bids)[i]} disabled={locked}
          aria-invalid={!!err} aria-describedby={err ? `${id}-err` : undefined}
          aria-label={`${kind === "v" ? "Valuation" : "Bid"} for advertiser ${IDS[i]} in rupees`}
          onChange={(e) => edit(kind, i, e.target.value)} />
        {err && <p id={`${id}-err`} className="mt-1 text-xs text-red-600">{err}</p>}
      </div>
    );
  };

  return <div className={`mx-auto ${compact ? "max-w-none space-y-7" : "max-w-5xl space-y-7"}`}>
    {!compact && <header><p className="text-sm font-semibold uppercase tracking-[.13em] text-indigo-700">Manual experiment</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-[#15213b]">Set bids and run an auction</h1><p className="mt-2 text-slate-600">Edit the four advertisers below. Auction ranking, payment, and payoffs are calculated by the backend.</p></header>}
    <section aria-label="Advertiser configuration" className="overflow-hidden rounded-2xl border border-[#e4e3df] bg-white shadow-[0_8px_26px_rgba(27,38,63,.045)]">
      <div className="border-b border-[#eeede9] px-5 py-5 sm:px-7"><p className="text-xs font-semibold uppercase tracking-[.14em] text-indigo-700">01 · Set up the auction</p><div className="mt-1 flex flex-wrap items-end justify-between gap-2"><div><h2 className="text-xl font-semibold tracking-tight text-[#182440]">Advertisers</h2><p className="mt-1 text-sm text-slate-500">Four bidders · values and bids in rupees per click (₹/click)</p></div><span className="rounded-full bg-[#f1f3f8] px-3 py-1 text-xs font-medium text-slate-600">Tie priority A → B → C → D</span></div></div>
      <div className="px-5 py-5 sm:px-7 sm:py-6">
        <div className="hidden grid-cols-[minmax(135px,1fr)_minmax(150px,1fr)_minmax(150px,1fr)_minmax(120px,.8fr)_auto] items-center gap-4 border-b border-slate-200 pb-3 text-xs font-semibold uppercase tracking-wide text-slate-500 sm:grid"><span>Advertiser</span><span>Valuation</span><span>Submitted bid</span><span>Strategy</span><span className="sr-only">Actions</span></div>
        <div className="grid gap-3 sm:gap-0">{IDS.map((id, i) => <div key={id} className="grid gap-3 rounded-xl border border-slate-200 bg-[#fdfdfc] p-4 sm:grid-cols-[minmax(135px,1fr)_minmax(150px,1fr)_minmax(150px,1fr)_minmax(120px,.8fr)_auto] sm:items-center sm:gap-4 sm:rounded-none sm:border-0 sm:border-b sm:bg-white sm:px-0 sm:py-4">
          <div className="flex items-center gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[#edf0f8] text-sm font-semibold text-[#334582]">{id}</span><div><p className="text-sm font-semibold text-[#1c2944]">Advertiser {id}</p><p className="text-xs text-slate-500 sm:hidden">Valuation (₹) · bid (₹)</p></div></div>
          <div><label className="mb-1 block text-xs font-medium text-slate-500 sm:sr-only" htmlFor={`v-${id}`}>True valuation (₹)</label>{field("v", i)}</div>
          <div><label className="mb-1 block text-xs font-medium text-slate-500 sm:sr-only" htmlFor={`b-${id}`}>Submitted bid (₹)</label>{field("b", i)}</div>
          <p className="text-sm text-slate-600">{(() => { const v = parseAmount(vals[i]); const b = parseAmount(bids[i]); if (!v.ok || !b.ok) return "Custom"; if (v.value === b.value) return "Truthful"; if (b.value > v.value) return "Overbid"; return v.value === 0 ? "Custom bid" : `Shaded · α ${(b.value / v.value).toFixed(2)}`; })()}</p>
          <Button className="min-h-10 justify-center rounded-lg sm:px-3" variant="outline" disabled={locked} onClick={() => truthfulOne(i)}>Bid truthfully</Button>
        </div>)}</div>
        {(mechanism === "gsp" || mechanism === "vcg") && <fieldset className="mt-5 rounded-xl border border-indigo-100 bg-indigo-50/40 p-4" aria-label="Advertisement slot click-through rates">
          <legend className="text-sm font-semibold text-[#1c2944]">Ad slot click-through rates</legend>
          <div className="mt-1 flex flex-wrap items-end justify-between gap-3"><p className="text-xs text-slate-600">Illustrative position rates: 1.00, 0.70, 0.40. Values are probabilities and must decrease by slot.</p>
            <label className="text-xs font-medium text-slate-600">Number of slots <select className="ml-2 min-h-9 rounded-lg border border-slate-300 bg-white px-2" value={clickThroughRates.length} disabled={locked} onChange={(e) => { const count = Number(e.target.value); setClickThroughRates((old) => Array.from({ length: count }, (_, i) => old[i] ?? ["1", "0.7", "0.4", "0.2"][i])); setResult(null); }} aria-label="Number of advertisement slots">{[1,2,3,4].map((n) => <option key={n}>{n}</option>)}</select></label>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">{clickThroughRates.map((rate, i) => <label key={i} className="text-xs font-medium text-slate-600">Slot {i + 1} CTR<input className="mt-1 min-h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm" inputMode="decimal" value={rate} disabled={locked} onChange={(e) => { setClickThroughRates((old) => old.map((value, j) => j === i ? e.target.value : value)); setResult(null); }} aria-label={`Click-through rate for slot ${i + 1}`} /></label>)}</div>
          <p className="mt-2 text-xs text-slate-500">Expected value and utility are ₹ per impression; bids and GSP prices are ₹ per click.</p>
        </fieldset>}
        <div className="mt-5 flex flex-col gap-4 border-t border-[#eeede9] pt-5">
          <div className="flex flex-wrap items-center gap-3"><Button variant="outline" className="min-h-10 rounded-lg" disabled={locked} onClick={truthfulAll}>All truthful</Button><div className="flex min-h-10 items-center gap-2"><label htmlFor="bid-fraction" className="whitespace-nowrap text-sm text-slate-600">Fixed fraction α</label><Input id="bid-fraction" className="h-10 w-24 rounded-lg" inputMode="decimal" value={fraction} disabled={locked} onChange={(e) => setFraction(e.target.value)} aria-label="Fixed bidding fraction from zero to one point five"/><Button className="min-h-10 rounded-lg" variant="outline" disabled={locked} onClick={applyFraction}>Apply to all</Button></div><Button variant="ghost" className="min-h-10 rounded-lg" disabled={locked} onClick={reset}><RotateCcw className="h-4 w-4" aria-hidden />Reset values</Button></div>
          <div className="flex flex-col gap-3 border-t border-[#eeede9] pt-4 sm:flex-row sm:items-center sm:justify-between"><p className="text-xs leading-5 text-slate-500">Inputs: ₹0–₹10,00,000 · at most two decimal places. Use fixed fractions to explore bid shading.</p><div className="flex gap-3"><Button className="min-h-12 flex-1 rounded-xl bg-indigo-700 px-7 text-base hover:bg-indigo-800 sm:flex-none" disabled={locked} onClick={onRun}>{running ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> : <Play className="h-5 w-5" aria-hidden />}{running ? "Running auction…" : "Run auction"}</Button>{animating && <Button variant="ghost" className="min-h-12" onClick={skip}>Skip animation</Button>}</div></div>
        </div>
        {Object.keys(errors).length > 0 && <p role="alert" className="mt-4 text-sm text-red-700">Fix the highlighted fields before running the auction.</p>}{apiError && <p role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{apiError}</p>}
      </div>
    </section>
    {running && <p className="flex items-center gap-2 text-sm text-indigo-800" role="status"><Loader2 className="h-4 w-4 animate-spin" aria-hidden />Auction request in progress.</p>}
    {result && <><RevealResults result={result} stage={stage} />{stage === "done" && <p className="text-sm text-slate-500">Saved to Experiment History.</p>}</>}
    {!result && !running && <div className="rounded-2xl border border-dashed border-slate-300 px-5 py-8 text-center"><p className="text-sm font-medium text-[#34415e]">The auction outcome will appear here</p><p className="mt-1 text-sm text-slate-500">Run the auction to reveal bid ranking, winner, payment, and payoffs.</p></div>}
  </div>;
}
