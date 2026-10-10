from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.auctions.models import Mechanism

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Alphas = Annotated[list[Number], Field(min_length=4, max_length=4)]
StrictInt = Annotated[int, Field(strict=True)]


class ValuationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["random", "fixed"] = "random"
    low: Number = 0
    high: Number = 100
    fixed_values: Alphas | None = None


class StrategyProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: Annotated[str, Field(min_length=1, max_length=60)]
    alphas: Alphas


class RunSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n_auctions: StrictInt = 1000
    mechanism: Literal["first_price", "second_price", "both"] = "both"
    valuation: ValuationSpec = ValuationSpec()
    seed: StrictInt | None = None
    profiles: Annotated[list[StrategyProfile], Field(min_length=1, max_length=8)]


class RevenueStats(BaseModel):
    mean: float; median: float; std: float; se: float; min: float; max: float


class Histogram(BaseModel):
    edges: list[float]; counts: list[int]


class Convergence(BaseModel):
    n: list[int]; mean: list[float]


class ResultBlock(BaseModel):
    profile_label: str
    alphas: list[float]
    mechanism: Mechanism
    n_auctions: int
    revenue: RevenueStats
    avg_winning_bid: float
    avg_winning_payment: float
    avg_winner_payoff: float
    avg_bidder_surplus: float
    highest_value_win_rate: float
    overbid_rate: float
    negative_winner_payoff_rate: float
    win_rate: dict[str, float]
    avg_payoff: dict[str, float]
    revenue_histogram: Histogram
    convergence: Convergence


class SimulationOut(BaseModel):
    n_auctions: int
    seed: int
    seed_was_generated: bool
    mechanisms: list[Mechanism]
    valuation: dict
    notes: list[str]
    definitions: dict[str, str]
    results: list[ResultBlock]


class SweepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n_auctions: StrictInt = 5000
    mechanism: Literal["first_price", "second_price", "both"] = "both"
    low: Number = 0
    high: Number = 100
    seed: StrictInt | None = None
    mode: Literal["all", "deviator"] = "all"
    deviator: Literal["A", "B", "C", "D"] = "A"
    others_alpha: Number = 1.0
    alphas: Annotated[list[Number], Field(min_length=1, max_length=60)] | None = None


class SweepOut(BaseModel):
    n_auctions: int
    seed: int
    seed_was_generated: bool
    mode: str
    deviator: str | None
    others_alpha: float | None
    valuation: dict
    points: dict[str, list[dict]]
