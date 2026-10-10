import type { Mechanism } from "../types/auction";
import type { SimulationOut, SweepOut } from "../types/simulation";

export const MECHANISMS: Mechanism[] = ["first_price", "second_price"];
export const mechanismName = (m: Mechanism) => m === "first_price" ? "First-price" : "Second-price";
export const advertiserIds = ["A", "B", "C", "D"] as const;

export function revenueRows(data: SimulationOut) {
  return data.results.map((r) => ({ strategy: r.profile_label, mechanism: mechanismName(r.mechanism), revenue: r.revenue.mean, se: r.revenue.se }));
}
export function payoffRows(data: SimulationOut, strategy: string) {
  return advertiserIds.map((advertiser) => ({ advertiser,
    firstPrice: data.results.find((r) => r.profile_label === strategy && r.mechanism === "first_price")?.avg_payoff[advertiser] ?? null,
    secondPrice: data.results.find((r) => r.profile_label === strategy && r.mechanism === "second_price")?.avg_payoff[advertiser] ?? null }));
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
  if (rows.some((r) => !r)) return [];
  return rows[0]!.convergence.n.map((n, i) => ({ n, firstPrice: rows[0]!.convergence.mean[i], secondPrice: rows[1]!.convergence.mean[i] }));
}
export function sensitivityRows(data: SweepOut) {
  return (data.points.first_price ?? []).map((p, i) => ({ alpha: p.alpha, firstPrice: p.deviator_mean_payoff, secondPrice: data.points.second_price?.[i]?.deviator_mean_payoff ?? null }));
}
