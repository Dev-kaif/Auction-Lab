"""Framework-independent calculations for a single four-advertiser auction."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from app.auctions.first_price import first_price_payment
from app.auctions.models import (
    ADVERTISERS,
    AdvertiserResult,
    AuctionResult,
    Mechanism,
    validate_vector,
)
from app.auctions.payoff import compute_payoffs, platform_revenue
from app.auctions.second_price import second_price_payment
from app.auctions.winner import determine_winner, ranking, runner_up_bid

ZERO_MONEY = Decimal("0.00")


def run_auction(
    valuations: Sequence[object],
    bids: Sequence[object],
    mechanism: Mechanism | str,
) -> AuctionResult:
    """Validate inputs, determine the result, and return all advertiser rows."""
    selected_mechanism = Mechanism(mechanism)
    values_by_advertiser = validate_vector(valuations, "valuations")
    bids_by_advertiser = validate_vector(bids, "bids")

    winner_index = determine_winner(bids_by_advertiser)
    winner_payment = _payment_for_winner(
        bids_by_advertiser,
        winner_index,
        selected_mechanism,
    )

    payments = [
        winner_payment if index == winner_index else ZERO_MONEY
        for index in range(len(bids_by_advertiser))
    ]
    payoffs = compute_payoffs(
        values_by_advertiser,
        payments,
        winner_index,
    )
    bidder_ranking = ranking(bids_by_advertiser)
    rank_by_index = {
        advertiser_index: rank
        for rank, advertiser_index in enumerate(bidder_ranking, start=1)
    }

    advertiser_results = tuple(
        AdvertiserResult(
            advertiser=ADVERTISERS[index],
            valuation=values_by_advertiser[index],
            bid=bids_by_advertiser[index],
            rank=rank_by_index[index],
            won=index == winner_index,
            payment=payments[index],
            payoff=payoffs[index],
            overbid=bids_by_advertiser[index] > values_by_advertiser[index],
        )
        for index in range(len(bids_by_advertiser))
    )

    winning_bid = bids_by_advertiser[winner_index]
    tied_advertisers = tuple(
        ADVERTISERS[index]
        for index, bid in enumerate(bids_by_advertiser)
        if bid == winning_bid
    )
    winner_payoff = payoffs[winner_index]
    payoff_sign = _payoff_sign(winner_payoff)
    highest_valuation = max(values_by_advertiser)

    return AuctionResult(
        mechanism=selected_mechanism,
        results=advertiser_results,
        winner_index=winner_index,
        winner=ADVERTISERS[winner_index],
        winning_bid=winning_bid,
        runner_up_bid=runner_up_bid(bids_by_advertiser, winner_index),
        payment=winner_payment,
        winner_payoff=winner_payoff,
        revenue=platform_revenue(payments),
        highest_valuation=highest_valuation,
        highest_valued_won=values_by_advertiser[winner_index] == highest_valuation,
        winner_surplus=winner_payoff,
        payoff_sign=payoff_sign,
        any_overbid=any(row.overbid for row in advertiser_results),
        tie_for_highest_bid=len(tied_advertisers) > 1,
        tied_bidders=tied_advertisers,
    )


def _payment_for_winner(
    bids: Sequence[Decimal],
    winner_index: int,
    mechanism: Mechanism,
) -> Decimal:
    """Apply the selected price rule after winner determination."""
    if mechanism is Mechanism.FIRST_PRICE:
        return first_price_payment(bids, winner_index)
    return second_price_payment(bids, winner_index)


def _payoff_sign(payoff: Decimal) -> str:
    """Return the sign label used by the API's result explanation."""
    if payoff > 0:
        return "positive"
    if payoff < 0:
        return "negative"
    return "zero"
