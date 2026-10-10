export type Mechanism = "first_price" | "second_price" | "gsp" | "vcg";

export interface AdvertiserOut {
  advertiser: string; valuation: string; bid: string; rank: number; won: boolean;
  outcome: "Won" | "Lost"; payment: string; payoff: string; overbid: boolean;
  slot?: number | null; click_through_rate?: number; payment_per_click?: string;
  expected_value?: string; expected_payment?: string; expected_utility?: string;
}

export interface AuctionOut {
  mechanism: Mechanism; advertisers: AdvertiserOut[]; winner: string; winning_bid: string;
  runner_up_bid: string; payment: string; winner_payoff: string; revenue: string;
  highest_valuation: string; highest_valued_won: boolean; winner_surplus: string;
  payoff_sign: "positive" | "zero" | "negative"; any_overbid: boolean;
  tie_for_highest_bid: boolean; tied_bidders: string[]; tie_break_rule: string;
  ranking: string[]; explanation: string; formulas: Record<string, string>;
  click_through_rates?: number[]; social_welfare?: string; is_multi_slot?: boolean;
}

export interface RunAuctionRequest { mechanism: Mechanism; valuations: number[]; bids: number[]; click_through_rates?: number[] }

export interface ExperimentSummary {
  id: string; created_at: string; experiment_type: "manual_auction" | "automatic_simulation";
  mechanism: string; strategy: string; metrics: Record<string, unknown>;
}
export interface ExperimentDetail extends ExperimentSummary {
  configuration: Record<string, unknown>; result: unknown;
}
export interface ExperimentList { items: ExperimentSummary[]; total: number }
export interface OverviewStats {
  total_experiments: number; manual_auctions: number; automatic_simulations: number; recent_experiments: ExperimentSummary[];
}
