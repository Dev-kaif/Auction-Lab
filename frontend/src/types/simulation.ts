import type { Mechanism } from "./auction";

export type MechanismChoice = Mechanism | "both";

export interface StrategyProfile { label: string; alphas: number[] }

export interface RunSimulationRequest {
  n_auctions: number;
  mechanism: MechanismChoice;
  valuation: { mode: "random"; low: number; high: number } | { mode: "fixed"; fixed_values: number[] };
  seed: number | null;
  profiles: StrategyProfile[];
}

export interface RevenueStats { mean: number; median: number; std: number; se: number; min: number; max: number }
export interface Histogram { edges: number[]; counts: number[] }
export interface Convergence { n: number[]; mean: number[] }

export interface ResultBlock {
  profile_label: string; alphas: number[]; mechanism: Mechanism; n_auctions: number;
  revenue: RevenueStats; avg_winning_bid: number; avg_winning_payment: number; avg_winner_payoff: number;
  avg_bidder_surplus: number; highest_value_win_rate: number; overbid_rate: number;
  negative_winner_payoff_rate: number; win_rate: Record<string, number>; avg_payoff: Record<string, number>;
  revenue_histogram: Histogram; convergence: Convergence;
}

export interface SimulationOut {
  n_auctions: number; seed: number; seed_was_generated: boolean; mechanisms: Mechanism[];
  valuation: { mode: "random" | "fixed"; low: number | null; high: number | null; distribution: string; fixed_values: number[] | null };
  notes: string[]; definitions: Record<string, string>; results: ResultBlock[];
}

export interface SweepRequest {
  n_auctions: number; mechanism: MechanismChoice; low: number; high: number; seed: number | null;
  mode: "all" | "deviator"; deviator: "A" | "B" | "C" | "D"; others_alpha: number; alphas: number[];
}
export interface SweepPoint {
  alpha: number; mean_revenue: number; mean_payoff_per_advertiser: number;
  deviator_mean_payoff: number | null; deviator_win_rate: number | null;
}
export interface SweepOut {
  n_auctions: number; seed: number; seed_was_generated: boolean; mode: string; deviator: string | null;
  others_alpha: number | null; valuation: SimulationOut["valuation"];
  points: Partial<Record<Mechanism, SweepPoint[]>>;
}
