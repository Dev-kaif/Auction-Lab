import { describe, expect, it } from "vitest";
import { convergenceRows, histogramRows, payoffRows, revenueRows, sensitivityRows, winRateRows } from "./analysis";
import type { SimulationOut, SweepOut } from "../types/simulation";

const block = (mechanism: "first_price" | "second_price", factor: number) => ({
  profile_label: "Truthful", alphas: [1, 1, 1, 1], mechanism, n_auctions: 2,
  revenue: { mean: 10 * factor, median: 10, std: 2, se: 1, min: 8, max: 12 }, avg_winning_bid: 10,
  avg_winning_payment: 10, avg_winner_payoff: 4, avg_bidder_surplus: 1, highest_value_win_rate: 1,
  overbid_rate: 0, negative_winner_payoff_rate: 0, win_rate: { A: 0.5, B: 0.5, C: 0, D: 0 },
  avg_payoff: { A: 2 * factor, B: 2, C: 0, D: 0 }, revenue_histogram: { edges: [0, 10, 20], counts: [1, 1] },
  convergence: { n: [1, 2], mean: [8, 10] },
});
const simulation = { n_auctions: 2, seed: 7, seed_was_generated: false, mechanisms: ["first_price", "second_price"],
  valuation: { mode: "random", low: 0, high: 20, distribution: "uniform", fixed_values: null }, notes: [], definitions: {},
  results: [block("first_price", 1), block("second_price", 2)] } as SimulationOut;

describe("analysis chart transformations", () => {
  it("maps backend revenue means and standard errors for each mechanism/profile", () => {
    expect(revenueRows(simulation)).toEqual([
      { strategy: "Truthful", mechanism: "First-price", revenue: 10, se: 1 },
      { strategy: "Truthful", mechanism: "Second-price", revenue: 20, se: 1 },
    ]);
  });
  it("keeps per-advertiser payoff and win rate distinct and uses backend denominators", () => {
    expect(payoffRows(simulation, "Truthful")[0]).toEqual({ advertiser: "A", firstPrice: 2, secondPrice: 4 });
    expect(winRateRows(simulation, "Truthful", "second_price")[0]).toEqual({ advertiser: "A", winRate: 0.5 });
  });
  it("maps API histogram bins and convergence checkpoints without creating observations", () => {
    expect(histogramRows(simulation, "Truthful", "first_price")).toEqual([
      { range: "0–10", midpoint: 5, count: 1 }, { range: "10–20", midpoint: 15, count: 1 },
    ]);
    expect(convergenceRows(simulation, "Truthful")).toEqual([{ n: 1, firstPrice: 8, secondPrice: 8 }, { n: 2, firstPrice: 10, secondPrice: 10 }]);
  });
  it("maps sensitivity payoff points returned from the sweep API", () => {
    const sweep = { points: { first_price: [{ alpha: 0.8, mean_revenue: 5, mean_payoff_per_advertiser: 1, deviator_mean_payoff: 2, deviator_win_rate: 0.4 }],
      second_price: [{ alpha: 0.8, mean_revenue: 6, mean_payoff_per_advertiser: 2, deviator_mean_payoff: 3, deviator_win_rate: 0.5 }] } } as SweepOut;
    expect(sensitivityRows(sweep)).toEqual([{ alpha: 0.8, firstPrice: 2, secondPrice: 3 }]);
  });
});
