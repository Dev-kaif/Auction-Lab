"""Framework-independent calculations for a single four-advertiser auction."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from app.auctions.first_price import first_price_payment
from app.auctions.models import (
    ADVERTISERS,
    DEFAULT_CLICK_THROUGH_RATES,
    AdvertiserResult,
    AuctionResult,
    Mechanism,
    validate_vector,
)
from app.auctions.multi_slot import allocate_slots
from app.auctions.payoff import compute_payoffs
from app.auctions.second_price import second_price_payment
from app.auctions.winner import determine_winner, ranking, runner_up_bid

ZERO_MONEY = Decimal("0.00")


def run_auction(
    valuations: Sequence[object],
    bids: Sequence[object],
    mechanism: Mechanism | str,
    click_through_rates: Sequence[float] = DEFAULT_CLICK_THROUGH_RATES,
) -> AuctionResult:
    """Validate inputs, determine the result, and return all advertiser rows."""
    selected_mechanism = Mechanism(mechanism)
    values_by_advertiser = validate_vector(valuations, "valuations")
    bids_by_advertiser = validate_vector(bids, "bids")

    winner_index = determine_winner(bids_by_advertiser)
    is_multi_slot = selected_mechanism in (Mechanism.GSP, Mechanism.VCG)
    if is_multi_slot:
        allocation = allocate_slots(
            values_by_advertiser, bids_by_advertiser, selected_mechanism, click_through_rates
        )
        payments = list(allocation.expected_payment)
        payoffs = list(allocation.expected_utility)
        winner_payment = payments[winner_index]
        winner_payoff = payoffs[winner_index]
        revenue = sum(payments, ZERO_MONEY)
    else:
        allocation = None
        winner_payment = _payment_for_winner(bids_by_advertiser, winner_index, selected_mechanism)
        payments = [winner_payment if index == winner_index else ZERO_MONEY for index in range(len(bids_by_advertiser))]
        payoffs = compute_payoffs(values_by_advertiser, payments, winner_index)
        winner_payoff = payoffs[winner_index]
        revenue = sum(payments, ZERO_MONEY)
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
            won=(allocation.slots[index] is not None) if allocation else index == winner_index,
            payment=payments[index],
            payoff=payoffs[index],
            overbid=bids_by_advertiser[index] > values_by_advertiser[index],
            slot=allocation.slots[index] if allocation else (1 if index == winner_index else None),
            click_through_rate=allocation.ctrs[index] if allocation else (1.0 if index == winner_index else 0.0),
            payment_per_click=allocation.price_per_click[index] if allocation else payments[index],
            expected_payment=payments[index],
            expected_utility=payoffs[index],
        )
        for index in range(len(bids_by_advertiser))
    )

    winning_bid = bids_by_advertiser[winner_index]
    tied_advertisers = tuple(
        ADVERTISERS[index]
        for index, bid in enumerate(bids_by_advertiser)
        if bid == winning_bid
    )
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
        revenue=revenue,
        highest_valuation=highest_valuation,
        highest_valued_won=(
            any(
                allocation.slots[index] is not None and values_by_advertiser[index] == highest_valuation
                for index in range(len(values_by_advertiser))
            ) if allocation else values_by_advertiser[winner_index] == highest_valuation
        ),
        winner_surplus=winner_payoff,
        payoff_sign=payoff_sign,
        any_overbid=any(row.overbid for row in advertiser_results),
        tie_for_highest_bid=len(tied_advertisers) > 1,
        tied_bidders=tied_advertisers,
        click_through_rates=tuple(click_through_rates) if is_multi_slot else (),
        social_welfare=allocation.social_welfare if allocation else values_by_advertiser[winner_index],
        is_multi_slot=is_multi_slot,
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
