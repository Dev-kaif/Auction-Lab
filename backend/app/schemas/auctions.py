from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.auctions.models import AuctionResult, Mechanism

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class RunAuctionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mechanism: Mechanism
    valuations: Annotated[list[Number], Field(min_length=4, max_length=4)]
    bids: Annotated[list[Number], Field(min_length=4, max_length=4)]


class AdvertiserOut(BaseModel):
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


def to_out(r: AuctionResult, explanation: str, formulas: dict[str, str]) -> AuctionOut:
    s = lambda d: f"{d:.2f}"  # noqa: E731 - exact Decimal -> 2dp string
    rows = [AdvertiserOut(advertiser=x.advertiser, valuation=s(x.valuation), bid=s(x.bid), rank=x.rank,
                          won=x.won, outcome="Won" if x.won else "Lost", payment=s(x.payment),
                          payoff=s(x.payoff), overbid=x.overbid) for x in r.results]
    return AuctionOut(
        mechanism=r.mechanism, advertisers=rows, winner=r.winner, winning_bid=s(r.winning_bid),
        runner_up_bid=s(r.runner_up_bid), payment=s(r.payment), winner_payoff=s(r.winner_payoff),
        revenue=s(r.revenue), highest_valuation=s(r.highest_valuation),
        highest_valued_won=r.highest_valued_won, winner_surplus=s(r.winner_surplus),
        payoff_sign=r.payoff_sign, any_overbid=r.any_overbid, tie_for_highest_bid=r.tie_for_highest_bid,
        tied_bidders=list(r.tied_bidders), tie_break_rule=r.tie_break_rule,
        ranking=[x.advertiser for x in sorted(r.results, key=lambda x: x.rank)],
        explanation=explanation, formulas=formulas,
    )
