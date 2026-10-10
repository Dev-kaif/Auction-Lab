import { useMemo, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ApiError, runSimulation, runSweep } from "../api/client";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { convergenceRows, histogramRows, payoffRows, sensitivityRows, winRateRows } from "../lib/analysis";
import type { Mechanism } from "../types/auction";
import type { SimulationOut, SweepOut } from "../types/simulation";

const colors = { first: "#4f46e5", second: "#0e7490", green: "#059669", orange: "#ea580c" };
const alphaGrid = Array.from({ length: 15 }, (_, i) => Number((0.3 + i * 0.05).toFixed(2)));
const selectClass = "rounded-md border border-slate-300 bg-white px-3 py-2 text-sm";

function ChartCard({ title, note, children }: { title: string; note: string; children: React.ReactNode }) {
  return <Card className="min-w-0 shadow-none"><CardHeader className="px-4 py-3"><CardTitle className="text-sm">{title}</CardTitle><p className="mt-1 text-[11px] text-navy-500">{note}</p></CardHeader><CardContent className="px-3 py-2"><div className="h-56 w-full min-w-0">{children}</div></CardContent></Card>;
}

export default function Analysis({ embedded = false }: { embedded?: boolean } = {}) {
  const [n, setN] = useState(1000); const [low, setLow] = useState("0"); const [high, setHigh] = useState("100"); const [seed, setSeed] = useState("");
  const [truthful, setTruthful] = useState(true); const [strategic, setStrategic] = useState(true);
  const [simulation, setSimulation] = useState<SimulationOut | null>(null); const [sweep, setSweep] = useState<SweepOut | null>(null);
  const [loading, setLoading] = useState(false); const [error, setError] = useState<string | null>(null);
  const [strategy, setStrategy] = useState(""); const [mechanism, setMechanism] = useState<Mechanism>("first_price");
  const profiles = useMemo(() => [
    ...(truthful ? [{ label: "Truthful (α=1)", alphas: [1, 1, 1, 1] }] : []),
    ...(strategic ? [{ label: "Strategic shading (α=0.8)", alphas: [0.8, 0.8, 0.8, 0.8] }] : []),
  ], [truthful, strategic]);

  const analyze = async () => {
    setError(null);
    if (!profiles.length) { setError("Select at least one bidding strategy."); return; }
    const lo = Number(low), hi = Number(high), parsedSeed = seed.trim() ? Number(seed) : null;
    if (!Number.isFinite(lo) || !Number.isFinite(hi) || hi <= lo || lo < 0 || hi > 1_000_000 || (parsedSeed !== null && (!Number.isInteger(parsedSeed) || parsedSeed < 0 || parsedSeed > 2_147_483_647))) {
      setError("Enter valid valuation bounds (0 ≤ lower < upper ≤ 1,000,000) and a seed from 0 to 2,147,483,647."); return;
    }
    setLoading(true); setSimulation(null); setSweep(null); setStrategy("");
    try {
      const result = await runSimulation({ n_auctions: n, mechanism: "both", valuation: { mode: "random", low: lo, high: hi }, seed: parsedSeed, profiles });
      const sensitivity = await runSweep({ n_auctions: n, mechanism: "both", low: lo, high: hi, seed: result.seed, mode: "deviator", deviator: "A", others_alpha: 1, alphas: alphaGrid });
      setSimulation(result); setSweep(sensitivity); setStrategy(profiles[0].label);
    } catch (e) { setError(e instanceof ApiError ? e.message : "Unexpected error while loading analysis."); }
    finally { setLoading(false); }
  };

  const strategies = simulation?.results.filter((r) => r.mechanism === "first_price").map((r) => r.profile_label) ?? [];
  const hist = simulation ? histogramRows(simulation, strategy, mechanism) : [];
  const convergence = simulation ? convergenceRows(simulation, strategy) : [];
  const sensitivity = sweep ? sensitivityRows(sweep) : [];
  const money = (v: number) => `₹${v.toFixed(2)}`;

  return <div className={`mx-auto ${embedded ? "max-w-none space-y-4" : "max-w-7xl space-y-6"}`}>
    {!embedded && <header><h1 className="text-2xl font-semibold">Analysis</h1><p className="mt-1 max-w-3xl text-sm text-navy-700">Compare auction mechanisms and bidding rules using paired Monte Carlo simulations from the auction engine.</p></header>}
    <Card className="shadow-none"><CardHeader className="px-4 py-3"><CardTitle className="text-sm">Sensitivity settings</CardTitle></CardHeader><CardContent className="space-y-3 px-4 py-3">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-xs font-medium">Auctions<select aria-label="Number of auctions" className={`${selectClass} mt-1 block w-full`} value={n} disabled={loading} onChange={(e) => setN(Number(e.target.value))}>{[100, 1000, 5000, 10000].map((v) => <option key={v} value={v}>{v.toLocaleString("en-IN")}</option>)}</select></label>
        <label className="text-xs font-medium">Lower valuation (₹)<input aria-label="Lower valuation" className={`${selectClass} mt-1 block w-full`} value={low} disabled={loading} onChange={(e) => setLow(e.target.value)} /></label>
        <label className="text-xs font-medium">Upper valuation (₹)<input aria-label="Upper valuation" className={`${selectClass} mt-1 block w-full`} value={high} disabled={loading} onChange={(e) => setHigh(e.target.value)} /></label>
        <label className="text-xs font-medium">Random seed (optional)<input aria-label="Random seed" className={`${selectClass} mt-1 block w-full`} value={seed} disabled={loading} onChange={(e) => setSeed(e.target.value)} /></label>
      </div>
      <fieldset disabled={loading} className="flex flex-wrap gap-x-5 gap-y-2 text-sm"><legend className="mb-2 text-xs font-medium">Bidding profiles (A, B, C and D use the same fraction)</legend>
        <label className="flex items-center gap-2"><input type="checkbox" checked={truthful} onChange={(e) => setTruthful(e.target.checked)} /> Truthful (α = 1)</label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={strategic} onChange={(e) => setStrategic(e.target.checked)} /> Strategic shading (α = 0.8)</label>
      </fieldset>
      <Button disabled={loading} onClick={() => void analyze()}>{loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Play className="h-4 w-4" aria-hidden />}{loading ? "Computing analysis…" : "Run analysis"}</Button>
      {loading && <p role="status" className="text-sm text-navy-600">Running paired simulations and bidding-fraction sweep…</p>}
      {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
    </CardContent></Card>
    {!simulation && !loading && !error && <Card><CardContent className="text-sm text-navy-500">No analysis yet. Choose settings and run an analysis to generate charts from the backend.</CardContent></Card>}
    {simulation && <>
      <p className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-navy-500">
        <span><b>Seed:</b> {simulation.seed}{simulation.seed_was_generated ? " (generated)" : " (provided)"}</span>
        <span><b>Valuations:</b> Uniform ₹{simulation.valuation.low}–₹{simulation.valuation.high}</span>
        <span>Shared scenarios across profiles and mechanisms · ties go to A first</span>
      </p>
      <details className="rounded-md border border-slate-200 bg-white">
        <summary className="cursor-pointer px-3 py-2 text-xs font-medium">Additional charts and sensitivity</summary>
        <div className="grid gap-3 border-t border-slate-100 p-3 xl:grid-cols-2">
        <ChartCard title="Average payoff per advertiser" note={`Mean payoff per auction, including zero payoff when that advertiser loses (₹). Strategy: ${strategy || "—"}. Separate mechanism series.`}>
          <div className="mb-2"><label className="sr-only" htmlFor="payoff-strategy">Strategy for advertiser payoff</label><select id="payoff-strategy" className={selectClass} value={strategy} onChange={(e) => setStrategy(e.target.value)}>{strategies.map((s) => <option key={s}>{s}</option>)}</select></div>
          <ResponsiveContainer width="100%" height="88%"><BarChart data={simulation ? payoffRows(simulation, strategy) : []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="advertiser" /><YAxis tickFormatter={money} /><Tooltip formatter={(v: number) => money(v)} /><Legend /><Bar dataKey="firstPrice" name="First-price" fill={colors.first} /><Bar dataKey="secondPrice" name="Second-price" fill={colors.second} /></BarChart></ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Win rate by advertiser" note={`Wins / completed auctions (percent). Strategy: ${strategy || "—"}; mechanism: ${mechanism === "first_price" ? "first-price" : "second-price"}. Sum is 100% with the engine's single-winner tie rule.`}>
          <div className="mb-2"><label className="sr-only" htmlFor="win-mechanism">Win rate mechanism</label><select id="win-mechanism" className={selectClass} value={mechanism} onChange={(e) => setMechanism(e.target.value as Mechanism)}><option value="first_price">First-price</option><option value="second_price">Second-price</option></select></div>
          <ResponsiveContainer width="100%" height="88%"><BarChart data={simulation ? winRateRows(simulation, strategy, mechanism) : []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="advertiser" /><YAxis domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} /><Tooltip formatter={(v: number) => `${(v * 100).toFixed(2)}%`} /><Bar dataKey="winRate" name="Win rate" fill={colors.green} /></BarChart></ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Revenue distribution" note={`Count of auctions in each revenue bin (₹). Strategy: ${strategy || "—"}; mechanism: ${mechanism === "first_price" ? "first-price" : "second-price"}. Bins use shared API histogram edges.`}>
          <ResponsiveContainer><BarChart data={hist}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="range" interval="preserveStartEnd" angle={-35} textAnchor="end" height={65} /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" name="Auctions" fill={colors.orange} /></BarChart></ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Strategy sensitivity" note="Advertiser A's mean payoff per auction (₹) as its bidding fraction α changes; B, C and D remain truthful. Same valuation draws in both mechanisms.">
          <ResponsiveContainer><LineChart data={sensitivity}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="alpha" label={{ value: "Bidding fraction α", position: "insideBottom", offset: -5 }} /><YAxis tickFormatter={money} /><Tooltip formatter={(v: number) => money(v)} /><Legend /><Line type="monotone" dataKey="firstPrice" name="First-price" stroke={colors.first} dot={false} /><Line type="monotone" dataKey="secondPrice" name="Second-price" stroke={colors.second} dot={false} /></LineChart></ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Revenue convergence" note={`Cumulative mean revenue (₹) by auction count; strategy: ${strategy || "—"}.`}>
          <ResponsiveContainer><LineChart data={convergence}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="n" /><YAxis tickFormatter={money} /><Tooltip formatter={(v: number) => money(v)} /><Legend /><Line type="monotone" dataKey="firstPrice" name="First-price" stroke={colors.first} dot={false} /><Line type="monotone" dataKey="secondPrice" name="Second-price" stroke={colors.second} dot={false} /></LineChart></ResponsiveContainer>
        </ChartCard>
      </div></details>
    </>}
  </div>;
}
