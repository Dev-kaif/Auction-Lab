"""Framework-independent auction engine."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from .first_price import first_price_payment
from .models import (
    ADVERTISERS,
    AdvertiserResult,
    AuctionResult,
    Mechanism,
    validate_vector,
)
from .payoff import compute_payoffs, platform_revenue
from .second_price import second_price_payment
from .winner import determine_winner, ranking, runner_up_bid

_ZERO = Decimal("0.00")


def run_auction(
    valuations: Sequence[object], bids: Sequence[object], mechanism: Mechanism | str
) -> AuctionResult:
    mech = Mechanism(mechanism)
    v = validate_vector(valuations, "valuations")
    b = validate_vector(bids, "bids")

    w = determine_winner(b)

    price = (
        first_price_payment(b, w)
        if mech is Mechanism.FIRST_PRICE
        else second_price_payment(b, w)
    )

    payments = [price if i == w else _ZERO for i in range(len(b))]
    payoffs = compute_payoffs(v, payments, w)

    order = ranking(b)
    rank_of = {idx: pos + 1 for pos, idx in enumerate(order)}
    
    rows = tuple(
        AdvertiserResult(
            advertiser=ADVERTISERS[i],
            valuation=v[i],
            bid=b[i],
            rank=rank_of[i],
            won=(i == w),
            payment=payments[i],
            payoff=payoffs[i],
            overbid=b[i] > v[i],
        )
        for i in range(len(b))
    )
    
    top_bid = b[w]
    tied = tuple(ADVERTISERS[i] for i in range(len(b)) if b[i] == top_bid)
    payoff = payoffs[w]
    sign = "positive" if payoff > 0 else "zero" if payoff == 0 else "negative"
    max_v = max(v)
    return AuctionResult(
        mechanism=mech,
        results=rows,
        winner_index=w,
        winner=ADVERTISERS[w],
        winning_bid=top_bid,
        runner_up_bid=runner_up_bid(b, w),
        payment=price,
        winner_payoff=payoff,
        revenue=platform_revenue(payments),
        highest_valuation=max_v,
        highest_valued_won=(v[w] == max_v),
        winner_surplus=payoff,
        payoff_sign=sign,
        any_overbid=any(r.overbid for r in rows),
        tie_for_highest_bid=len(tied) > 1,
        tied_bidders=tied,
    )
