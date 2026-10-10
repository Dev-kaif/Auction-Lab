import type { Mechanism } from "../types/auction";
import type { SimulationOut, SweepOut } from "../types/simulation";

export const MECHANISMS: Mechanism[] = ["first_price", "second_price", "gsp", "vcg"];
export const mechanismName = (m: Mechanism) => ({ first_price: "First-price", second_price: "Second-price", gsp: "GSP", vcg: "VCG" } as const)[m];
export const advertiserIds = ["A", "B", "C", "D"] as const;
const chartKey = (m: Mechanism) => m === "first_price" ? "firstPrice" : m === "second_price" ? "secondPrice" : m;

export function revenueRows(data: SimulationOut) {
  return data.results.map((r) => ({ strategy: r.profile_label, mechanism: mechanismName(r.mechanism), revenue: r.revenue.mean, se: r.revenue.se }));
}
export function payoffRows(data: SimulationOut, strategy: string) {
  return advertiserIds.map((advertiser) => {
    const values: Record<string, string | number | null> = { advertiser };
    for (const mechanism of MECHANISMS) {
      const result = data.results.find((r) => r.profile_label === strategy && r.mechanism === mechanism);
      if (result) values[chartKey(mechanism)] = result.avg_payoff[advertiser] ?? null;
    }
    return values;
  });
}
export function winRateRows(data: SimulationOut, strategy: string, mechanism: Mechanism) {
  return advertiserIds.map((advertiser) => ({ advertiser, winRate: data.results.find((r) => r.profile_label === strategy && r.mechanism === mechanism)?.win_rate[advertiser] ?? null }));
}
export function histogramRows(data: SimulationOut, strategy: string, mechanism: Mechanism) {
  const h = data.results.find((r) => r.profile_label === strategy && r.mechanism === mechanism)?.revenue_histogram;
  if (!h) return [];
  return h.counts.map((count, i) => ({ range: `${h.edges[i].toFixed(0)}–${h.edges[i + 1].toFixed(0)}`, midpoint: (h.edges[i] + h.edges[i + 1]) / 2, count }));
}
export function convergenceRows(data: SimulationOut, strategy: string) {
  const rows = MECHANISMS.map((mechanism) => data.results.find((r) => r.profile_label === strategy && r.mechanism === mechanism));
  const reference = rows.find((r) => r);
  if (!reference) return [];
  return reference.convergence.n.map((n, i) => Object.fromEntries([
    ["n", n], ...rows.flatMap((r, index) => r ? [[chartKey(MECHANISMS[index]), r.convergence.mean[i]]] : []),
  ]));
}
export function sensitivityRows(data: SweepOut) {
  const reference = Object.values(data.points)[0] ?? [];
  return reference.map((p, i) => Object.fromEntries([
    ["alpha", p.alpha], ...MECHANISMS.flatMap((mechanism) => {
      const point = data.points[mechanism]?.[i];
      return point ? [[chartKey(mechanism), point.deviator_mean_payoff]] : [];
    }),
  ]));
}
