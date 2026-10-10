export type Mechanism = "first_price" | "second_price";

export interface AdvertiserOut {
  advertiser: string; valuation: string; bid: string; rank: number; won: boolean;
  outcome: "Won" | "Lost"; payment: string; payoff: string; overbid: boolean;
}

export interface AuctionOut {
  mechanism: Mechanism; advertisers: AdvertiserOut[]; winner: string; winning_bid: string;
  runner_up_bid: string; payment: string; winner_payoff: string; revenue: string;
  highest_valuation: string; highest_valued_won: boolean; winner_surplus: string;
  payoff_sign: "positive" | "zero" | "negative"; any_overbid: boolean;
  tie_for_highest_bid: boolean; tied_bidders: string[]; tie_break_rule: string;
  ranking: string[]; explanation: string; formulas: Record<string, string>;
}

export interface RunAuctionRequest { mechanism: Mechanism; valuations: number[]; bids: number[] }

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
