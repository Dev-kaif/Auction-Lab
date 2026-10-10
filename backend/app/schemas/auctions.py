"""Validated request and response models for a single auction."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from app.auctions.models import AuctionResult, Mechanism

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class RunAuctionRequest(BaseModel):
    """The user-supplied mechanism, valuations, and bids for advertisers A–D."""

    model_config = ConfigDict(extra="forbid")

    mechanism: Mechanism
    valuations: Annotated[list[Number], Field(min_length=4, max_length=4)]
    bids: Annotated[list[Number], Field(min_length=4, max_length=4)]


class AdvertiserOut(BaseModel):
    """One advertiser's calculated outcome in a completed auction."""

    advertiser: str
    valuation: str
    bid: str
    rank: int
    won: bool
    outcome: str
    payment: str
    payoff: str
    overbid: bool


class AuctionOut(BaseModel):
    """The winner, payment rule, payoff details, and formulas for one auction."""

    mechanism: Mechanism
    advertisers: list[AdvertiserOut]
    winner: str
    winning_bid: str
    runner_up_bid: str
    payment: str
    winner_payoff: str
    revenue: str
    highest_valuation: str
    highest_valued_won: bool
    winner_surplus: str
    payoff_sign: str
    any_overbid: bool
    tie_for_highest_bid: bool
    tied_bidders: list[str]
    tie_break_rule: str
    ranking: list[str]
    explanation: str
    formulas: dict[str, str]


def to_out(
    result: AuctionResult,
    explanation: str,
    formulas: dict[str, str],
) -> AuctionOut:
    """Serialize exact Decimal outcomes as two-decimal currency strings."""
    def money_text(value: Any) -> str:
        return f"{value:.2f}"

    advertiser_rows = [
        AdvertiserOut(
            advertiser=advertiser.advertiser,
            valuation=money_text(advertiser.valuation),
            bid=money_text(advertiser.bid),
            rank=advertiser.rank,
            won=advertiser.won,
            outcome="Won" if advertiser.won else "Lost",
            payment=money_text(advertiser.payment),
            payoff=money_text(advertiser.payoff),
            overbid=advertiser.overbid,
        )
        for advertiser in result.results
    ]
    ranked_advertisers = sorted(
        result.results,
        key=lambda advertiser: advertiser.rank,
    )

    return AuctionOut(
        mechanism=result.mechanism,
        advertisers=advertiser_rows,
        winner=result.winner,
        winning_bid=money_text(result.winning_bid),
        runner_up_bid=money_text(result.runner_up_bid),
        payment=money_text(result.payment),
        winner_payoff=money_text(result.winner_payoff),
        revenue=money_text(result.revenue),
        highest_valuation=money_text(result.highest_valuation),
        highest_valued_won=result.highest_valued_won,
        winner_surplus=money_text(result.winner_surplus),
        payoff_sign=result.payoff_sign,
        any_overbid=result.any_overbid,
        tie_for_highest_bid=result.tie_for_highest_bid,
        tied_bidders=list(result.tied_bidders),
        tie_break_rule=result.tie_break_rule,
        ranking=[advertiser.advertiser for advertiser in ranked_advertisers],
        explanation=explanation,
        formulas=formulas,
    )
