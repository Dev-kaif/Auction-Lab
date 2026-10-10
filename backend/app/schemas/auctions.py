"""Validated request and response models for a single auction."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auctions.models import AuctionResult, DEFAULT_CLICK_THROUGH_RATES, Mechanism, validate_click_through_rates

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class RunAuctionRequest(BaseModel):
    """The user-supplied mechanism, valuations, and bids for advertisers A–D."""

    model_config = ConfigDict(extra="forbid")

    mechanism: Mechanism
    valuations: Annotated[list[Number], Field(min_length=4, max_length=4)]
    bids: Annotated[list[Number], Field(min_length=4, max_length=4)]
    click_through_rates: list[Number] = Field(default_factory=lambda: list(DEFAULT_CLICK_THROUGH_RATES))

    @field_validator("click_through_rates")
    @classmethod
    def valid_click_through_rates(cls, values: list[float]) -> list[float]:
        return list(validate_click_through_rates(values))


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
    slot: int | None = None
    click_through_rate: float = 0.0
    payment_per_click: str = "0.00"
    expected_value: str = "0.00"
    expected_payment: str = "0.00"
    expected_utility: str = "0.00"


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
    click_through_rates: list[float] = Field(default_factory=list)
    social_welfare: str = "0.00"
    is_multi_slot: bool = False


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
            slot=advertiser.slot,
            click_through_rate=advertiser.click_through_rate,
            payment_per_click=money_text(advertiser.payment_per_click),
            expected_value=money_text(
                (advertiser.valuation * Decimal(str(advertiser.click_through_rate))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            ),
            expected_payment=money_text(advertiser.expected_payment),
            expected_utility=money_text(advertiser.expected_utility),
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
        click_through_rates=list(result.click_through_rates),
        social_welfare=money_text(result.social_welfare),
        is_multi_slot=result.is_multi_slot,
    )
