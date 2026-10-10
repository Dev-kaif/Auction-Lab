import { RefreshCw } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ErrorBar, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ResultBlock, SimulationOut } from "../../types/simulation";
import { Button } from "../ui/button";

const rupees = (x: number) => `${x < 0 ? "−" : ""}₹${Math.abs(x).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const mechName = (m: string) => m === "first_price" ? "First-price" : "Second-price";
const chartRows = (groups: ResultBlock[]) => {
  const rows = new Map<string, { strategy: string; firstPrice?: number; secondPrice?: number; firstSe?: number; secondSe?: number }>();
  groups.forEach((g) => {
    const row = rows.get(g.profile_label) ?? { strategy: g.profile_label };
    if (g.mechanism === "first_price") { row.firstPrice = g.revenue.mean; row.firstSe = g.revenue.se; }
    else { row.secondPrice = g.revenue.mean; row.secondSe = g.revenue.se; }
    rows.set(g.profile_label, row);
  });
  return [...rows.values()];
};

const prominentMetrics = [
  { key: "revenue", label: "Platform revenue", unit: "₹ per auction", value: (g: ResultBlock) => rupees(g.revenue.mean) },
  { key: "winner", label: "Winner payoff", unit: "₹ per auction · winner only", value: (g: ResultBlock) => rupees(g.avg_winner_payoff) },
  { key: "bidder", label: "Mean payoff per advertiser", unit: "₹ per advertiser-auction", value: (g: ResultBlock) => rupees(g.avg_bidder_surplus) },
];
const secondaryMetrics: [string, (g: ResultBlock) => string][] = [
  ["Median revenue (₹ / auction)", (g) => rupees(g.revenue.median)], ["Revenue standard deviation (₹)", (g) => rupees(g.revenue.std)],
  ["Highest-value win rate", (g) => `${(g.highest_value_win_rate * 100).toFixed(1)}%`], ["Auctions with any overbid", (g) => `${(g.overbid_rate * 100).toFixed(1)}%`],
  ["Negative winner payoff rate", (g) => `${(g.negative_winner_payoff_rate * 100).toFixed(1)}%`],
  ...["A", "B", "C", "D"].map((id): [string, (g: ResultBlock) => string] => [`Win rate · ${id}`, (g) => `${(g.win_rate[id] * 100).toFixed(1)}%`]),
  ...["A", "B", "C", "D"].map((id): [string, (g: ResultBlock) => string] => [`Mean payoff · ${id} (₹ / auction)`, (g) => rupees(g.avg_payoff[id])]),
];

export default function SimulationResults({ data, onRerun, busy }: { data: SimulationOut; onRerun: (seed: number) => void; busy: boolean }) {
  const groups = data.results;
  if (!groups.length) return <section aria-label="Simulation results" className="rounded-2xl border border-amber-200 bg-amber-50 p-5"><h2 className="font-semibold text-amber-950">No comparable results returned</h2><p className="mt-1 text-sm text-amber-900">The simulation completed but returned no result groups for these settings. Check the selected strategies and mechanisms.</p></section>;
  const chart = chartRows(groups);
  return <section aria-label="Simulation results" className="min-w-0 space-y-6">
    <header className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[.14em] text-indigo-700">02 · Inspect the results</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-[#182440]">Simulation results</h2></div><Button variant="outline" className="min-h-11 rounded-xl" disabled={busy} onClick={() => onRerun(data.seed)}><RefreshCw className="h-4 w-4" aria-hidden />Rerun seed {data.seed}</Button></header>
    <div className="flex flex-wrap gap-x-5 gap-y-2 rounded-xl bg-[#eeeff3] px-4 py-3 text-sm text-slate-700" aria-label="Experiment settings">
      <span><b className="font-semibold text-slate-900">Auctions</b> · {data.n_auctions.toLocaleString("en-IN")} per profile</span><span><b className="font-semibold text-slate-900">Mechanisms</b> · {data.mechanisms.map(mechName).join(" + ")}</span><span><b className="font-semibold text-slate-900">Seed</b> · {data.seed}{data.seed_was_generated ? " (generated)" : ""}</span>
      {data.valuation.mode === "random" ? <span><b className="font-semibold text-slate-900">Values</b> · Uniform ₹{data.valuation.low}–₹{data.valuation.high}</span> : <span><b className="font-semibold text-slate-900">Fixed values</b> · {data.valuation.fixed_values?.map((v, i) => `${"ABCD"[i]} ₹${v}`).join(" · ")}</span>}
    </div>
    {data.notes.map((note) => <p key={note} role="note" className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">{note}</p>)}

    <div className="grid gap-4 md:grid-cols-3" aria-label="Headline metrics">
      {prominentMetrics.map((metric) => <div key={metric.key} className="border-l-[3px] border-indigo-600 bg-white px-4 py-3"><p className="text-sm font-medium text-slate-600">{metric.label}</p><p className="mt-1 text-2xl font-semibold tracking-tight tabular-nums text-[#182440]">{metric.value(groups[0])}</p><p className="mt-1 text-xs text-slate-500">{metric.unit} · {mechName(groups[0].mechanism)}, {groups[0].profile_label}</p></div>)}
    </div>

    <section aria-label="Average platform revenue comparison" className="rounded-2xl border border-[#e4e3df] bg-white p-5 shadow-[0_5px_20px_rgba(27,38,63,.035)] sm:p-7">
      <div className="mb-4"><p className="text-xs font-semibold uppercase tracking-[.12em] text-teal-700">Strategy comparison</p><h3 className="mt-1 text-xl font-semibold tracking-tight text-[#182440]">How do bidding strategies change platform revenue?</h3><p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">Mean seller revenue for each strategy and mechanism, on matched valuation draws. Error bars show ±1 standard error. Currency: Indian rupees per auction.</p></div>
      <div className="h-[320px] w-full min-w-0 sm:h-[380px]" role="img" aria-label="Grouped bar chart of mean platform revenue by strategy. Indigo bars show first-price and teal bars show second-price auctions.">
        <ResponsiveContainer width="100%" height="100%"><BarChart data={chart} margin={{ top: 10, right: 12, bottom: 34, left: 16 }} barGap={5}>
          <CartesianGrid stroke="#e9ebf0" strokeDasharray="4 5" vertical={false} />
          <XAxis dataKey="strategy" interval={0} tick={{ fill: "#48546c", fontSize: 12 }} tickLine={false} axisLine={{ stroke: "#cbd0da" }} angle={chart.length > 3 ? -12 : 0} textAnchor={chart.length > 3 ? "end" : "middle"} height={58} />
          <YAxis tick={{ fill: "#667085", fontSize: 12 }} width={68} tickFormatter={(v) => `₹${Number(v).toLocaleString("en-IN")}`} tickLine={false} axisLine={false} label={{ value: "Revenue (₹ / auction)", angle: -90, position: "insideLeft", offset: 0, fill: "#667085", fontSize: 12 }} />
          <Tooltip formatter={(v: number, name: string) => [rupees(v), name]} labelStyle={{ color: "#182440", fontWeight: 600 }} contentStyle={{ border: "1px solid #dfe2e8", borderRadius: 12, boxShadow: "0 8px 24px rgba(22,34,61,.1)" }} />
          <Legend verticalAlign="top" align="right" wrapperStyle={{ paddingBottom: 12, color: "#34415e", fontSize: 13 }} />
          <Bar dataKey="firstPrice" name="First-price" fill="#4f46e5" radius={[5, 5, 0, 0]} maxBarSize={62}><ErrorBar dataKey="firstSe" width={5} stroke="#312e81" /></Bar>
          <Bar dataKey="secondPrice" name="Second-price" fill="#0e7490" radius={[5, 5, 0, 0]} maxBarSize={62}><ErrorBar dataKey="secondSe" width={5} stroke="#164e63" /></Bar>
        </BarChart></ResponsiveContainer>
      </div>
    </section>

    <section aria-label="Aggregate results by strategy" className="rounded-2xl border border-[#e4e3df] bg-white p-5 sm:p-7">
      <div className="mb-4"><h3 className="text-lg font-semibold text-[#182440]">Results by mechanism and strategy</h3><p className="mt-1 text-sm text-slate-500">Compare central outcomes and win rates for all advertisers.</p></div>
      <div className="hidden overflow-x-auto md:block"><table className="w-full min-w-[900px] border-separate border-spacing-0 text-sm"><thead><tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500"><th scope="col" className="border-b border-slate-200 px-3 py-3">Mechanism</th><th scope="col" className="border-b border-slate-200 px-3 py-3">Strategy · fractions A–D</th><th scope="col" className="border-b border-slate-200 px-3 py-3 text-right">Mean revenue</th><th scope="col" className="border-b border-slate-200 px-3 py-3 text-right">Winner payoff</th><th scope="col" className="border-b border-slate-200 px-3 py-3 text-right">Payoff / advertiser</th>{["A", "B", "C", "D"].map((id) => <th key={id} scope="col" className="border-b border-slate-200 px-3 py-3 text-right">{id} win rate</th>)}</tr></thead><tbody>{groups.map((g) => <tr key={`${g.profile_label}|${g.mechanism}`} className="odd:bg-[#fafaf8]"><th scope="row" className="border-b border-slate-100 px-3 py-4 text-left font-semibold text-[#293854]">{mechName(g.mechanism)}</th><td className="max-w-[250px] border-b border-slate-100 px-3 py-4 text-slate-700">{g.profile_label}<span className="mt-1 block text-xs tabular-nums text-slate-500">α [{g.alphas.join(", ")}]</span></td><td className="border-b border-slate-100 px-3 py-4 text-right tabular-nums">{rupees(g.revenue.mean)} <span className="text-xs text-slate-500">± {rupees(g.revenue.se)}</span></td><td className="border-b border-slate-100 px-3 py-4 text-right tabular-nums">{rupees(g.avg_winner_payoff)}</td><td className="border-b border-slate-100 px-3 py-4 text-right tabular-nums">{rupees(g.avg_bidder_surplus)}</td>{["A", "B", "C", "D"].map((id) => <td key={id} className="border-b border-slate-100 px-3 py-4 text-right tabular-nums">{(g.win_rate[id] * 100).toFixed(1)}%</td>)}</tr>)}</tbody></table></div>
      <div className="space-y-3 md:hidden">{groups.map((g) => <article key={`${g.profile_label}|${g.mechanism}`} className="rounded-xl border border-slate-200 p-4"><div className="flex items-start justify-between gap-3"><div><h4 className="font-semibold text-[#23314c]">{mechName(g.mechanism)}</h4><p className="mt-0.5 text-sm text-slate-600">{g.profile_label}</p><p className="mt-1 text-xs tabular-nums text-slate-500">Fractions A–D: {g.alphas.join(", ")}</p></div></div><dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-slate-100 pt-3 text-sm"><div><dt className="text-xs text-slate-500">Revenue / auction</dt><dd className="mt-0.5 font-medium tabular-nums">{rupees(g.revenue.mean)} <span className="text-xs text-slate-500">± {rupees(g.revenue.se)}</span></dd></div><div><dt className="text-xs text-slate-500">Winner payoff</dt><dd className="mt-0.5 font-medium tabular-nums">{rupees(g.avg_winner_payoff)}</dd></div><div><dt className="text-xs text-slate-500">Payoff / advertiser</dt><dd className="mt-0.5 font-medium tabular-nums">{rupees(g.avg_bidder_surplus)}</dd></div></dl><div className="mt-3 border-t border-slate-100 pt-3"><p className="text-xs font-medium text-slate-500">Win rate by advertiser</p><div className="mt-2 grid grid-cols-4 gap-2">{["A", "B", "C", "D"].map((id) => <div key={id} className="rounded-lg bg-slate-50 px-2 py-2 text-center"><p className="text-xs text-slate-500">{id}</p><p className="mt-0.5 text-sm font-semibold tabular-nums text-[#263550]">{(g.win_rate[id] * 100).toFixed(1)}%</p></div>)}</div></div></article>)}</div>
      <p className="mt-4 text-xs leading-5 text-slate-500">Winner payoff is averaged over auctions for the winning advertiser only. Payoff per advertiser averages all four advertisers across auctions, including zero payoffs when they lose.</p>
    </section>

    <details className="rounded-2xl border border-[#e4e3df] bg-white"><summary className="cursor-pointer px-5 py-4 text-sm font-semibold text-[#283550] sm:px-7">Explore secondary metrics and metric definitions</summary><div className="overflow-x-auto border-t border-slate-100 p-5 sm:p-7"><table className="w-full min-w-[700px] text-sm"><thead><tr className="text-left text-xs text-slate-500"><th scope="col" className="py-2 pr-4">Metric</th>{groups.map((g) => <th scope="col" key={`${g.profile_label}|${g.mechanism}`} className="px-2 py-2 text-right">{mechName(g.mechanism)} · {g.profile_label}</th>)}</tr></thead><tbody>{secondaryMetrics.map(([label, get]) => <tr key={label} className="border-t border-slate-100"><th scope="row" className="py-2 pr-4 text-left font-normal text-slate-700">{label}</th>{groups.map((g) => <td key={`${g.profile_label}|${g.mechanism}`} className="px-2 py-2 text-right tabular-nums text-slate-700">{get(g)}</td>)}</tr>)}</tbody></table><dl className="mt-5 grid gap-x-6 gap-y-2 text-xs leading-5 text-slate-600 sm:grid-cols-2">{Object.entries(data.definitions).map(([name, definition]) => <div key={name}><dt className="inline font-mono font-semibold text-slate-800">{name}: </dt><dd className="inline">{definition}</dd></div>)}</dl></div></details>
    <p className="text-xs text-slate-500">Completed simulation saved to Experiment History.</p>
  </section>;
}
