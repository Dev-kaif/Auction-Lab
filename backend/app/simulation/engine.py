"""Fast NumPy auction engine for evaluating many auctions at once."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from app.auctions.models import (AuctionInputError, DEFAULT_CLICK_THROUGH_RATES, Mechanism,
                                 N_ADVERTISERS, validate_click_through_rates)
from app.auctions.strategies import validate_alpha


@dataclass(frozen=True)
class Batch:
    """Auction outcomes stored as arrays, one row per simulated auction."""

    winner: np.ndarray  # (n,) winner index: A=0, B=1, C=2, D=3
    winning_bid: np.ndarray  # (n,) highest bid in each auction
    runner_up_bid: np.ndarray  # (n,) second-highest bid
    payment: np.ndarray  # (n,) single-slot payment or total multi-slot expected payment
    payoffs: np.ndarray  # (n, 4) utility per advertiser; unallocated bidders receive zero
    revenue: np.ndarray  # (n,) platform revenue per auction/impression
    slot_assignment: np.ndarray  # (n, 4), one-based slot or -1 for unallocated
    assigned_ctr: np.ndarray  # (n, 4), zero for unallocated advertisers
    payment_per_click: np.ndarray  # (n, 4)
    expected_payments: np.ndarray  # (n, 4), rupees per impression
    social_welfare: np.ndarray  # (n,), expected true value per impression


def parse_alphas(alphas: object) -> np.ndarray:
    """Validate and convert the four advertiser bidding fractions to floats."""
    fractions = list(alphas)  # type: ignore[call-overload]
    if len(fractions) != N_ADVERTISERS:
        raise AuctionInputError(
            f"alphas must contain exactly {N_ADVERTISERS} values"
        )

    return np.array([float(validate_alpha(value)) for value in fractions])


def bids_from_alphas(
    valuations: np.ndarray,
    alphas: np.ndarray,
) -> np.ndarray:
    """Apply each advertiser's fraction to their valuation and round to paise."""
    return np.round(valuations * alphas[None, :], 2)


def run_batch(
    valuations: np.ndarray,
    bids: np.ndarray,
    mechanism: Mechanism | str,
    click_through_rates: Sequence[float] = DEFAULT_CLICK_THROUGH_RATES,
) -> Batch:
    """Calculate winner, payment, payoff, and revenue for each matrix row."""
    selected_mechanism = Mechanism(mechanism)
    expected_columns = N_ADVERTISERS
    matrices_match = (
        valuations.shape == bids.shape
        and valuations.ndim == 2
        and valuations.shape[1] == expected_columns
    )
    if not matrices_match:
        raise AuctionInputError(
            "valuations and bids must both have shape (n_auctions, 4)"
        )

    auction_count = valuations.shape[0]
    auction_rows = np.arange(auction_count)

    # np.argmax returns the first index on a tie, matching A → B → C → D.
    winner_indices = np.argmax(bids, axis=1)
    sorted_bids = np.sort(bids, axis=1)
    highest_bids = sorted_bids[:, -1]
    second_highest_bids = sorted_bids[:, -2]

    if selected_mechanism in (Mechanism.GSP, Mechanism.VCG):
        rates = np.asarray(validate_click_through_rates(click_through_rates), dtype=float)
        ranked = np.argsort(-bids, axis=1, kind="stable")
        ranks = np.argsort(ranked, axis=1, kind="stable")
        slot_count = len(rates)
        slot_assignment = np.where(ranks < slot_count, ranks + 1, -1)
        assigned_ctr = np.zeros_like(valuations, dtype=float)
        allocated = ranks < slot_count
        assigned_ctr[allocated] = rates[ranks[allocated]]

        payment_per_click = np.zeros_like(valuations, dtype=float)
        expected_payments = np.zeros_like(valuations, dtype=float)
        if selected_mechanism is Mechanism.GSP:
            has_next_bidder = ranks + 1 < N_ADVERTISERS
            next_rank = np.minimum(ranks + 1, N_ADVERTISERS - 1)
            next_bid = np.take_along_axis(bids, np.take_along_axis(ranked, next_rank, axis=1), axis=1)
            payment_per_click[allocated & has_next_bidder] = next_bid[allocated & has_next_bidder]
            expected_payments = payment_per_click * assigned_ctr
        else:
            # VCG externalities are calculated in expected value per impression.
            weighted_allocated_bid = assigned_ctr * bids
            total_allocated_bid_welfare = weighted_allocated_bid.sum(axis=1)
            rows = np.arange(auction_count)
            for advertiser in range(N_ADVERTISERS):
                without_i_order = np.argsort(-np.where(
                    np.arange(N_ADVERTISERS)[None, :] == advertiser, -np.inf, bids
                ), axis=1, kind="stable")
                without_i_order = np.array([
                    order[order != advertiser][:slot_count] for order in without_i_order
                ])
                without_i_count = without_i_order.shape[1]
                without_welfare = np.zeros(auction_count, dtype=float)
                if without_i_count:
                    without_welfare = (bids[rows[:, None], without_i_order] * rates[:without_i_count]).sum(axis=1)
                others_welfare_with_i = total_allocated_bid_welfare - weighted_allocated_bid[:, advertiser]
                expected_payments[:, advertiser] = np.maximum(0.0, without_welfare - others_welfare_with_i)
                ctr = assigned_ctr[:, advertiser]
                payment_per_click[:, advertiser] = np.divide(
                    expected_payments[:, advertiser], ctr,
                    out=np.zeros(auction_count, dtype=float), where=ctr > 0,
                )

        payoffs = valuations * assigned_ctr - expected_payments
        payments = expected_payments.sum(axis=1)
        social_welfare = (valuations * assigned_ctr).sum(axis=1)
        winner_indices = ranked[:, 0]
        winning_bids = highest_bids
        runner_bids = second_highest_bids
    elif selected_mechanism is Mechanism.FIRST_PRICE:
        payments = highest_bids
        slot_assignment = np.full_like(valuations, -1, dtype=int)
        slot_assignment[auction_rows, winner_indices] = 1
        assigned_ctr = np.zeros_like(valuations, dtype=float)
        assigned_ctr[auction_rows, winner_indices] = 1.0
        payment_per_click = np.zeros_like(valuations, dtype=float)
        payment_per_click[auction_rows, winner_indices] = payments
        expected_payments = np.zeros_like(valuations, dtype=float)
        expected_payments[auction_rows, winner_indices] = payments
        social_welfare = valuations[auction_rows, winner_indices].copy()
    else:
        # When top bids tie, the runner-up is also the top bid.
        payments = second_highest_bids
        slot_assignment = np.full_like(valuations, -1, dtype=int)
        slot_assignment[auction_rows, winner_indices] = 1
        assigned_ctr = np.zeros_like(valuations, dtype=float)
        assigned_ctr[auction_rows, winner_indices] = 1.0
        payment_per_click = np.zeros_like(valuations, dtype=float)
        payment_per_click[auction_rows, winner_indices] = payments
        expected_payments = np.zeros_like(valuations, dtype=float)
        expected_payments[auction_rows, winner_indices] = payments
        social_welfare = valuations[auction_rows, winner_indices].copy()

    if selected_mechanism not in (Mechanism.GSP, Mechanism.VCG):
        payoffs = np.zeros_like(valuations, dtype=float)
        payoffs[auction_rows, winner_indices] = valuations[auction_rows, winner_indices] - payments

    return Batch(
        winner=winner_indices,
        winning_bid=highest_bids,
        runner_up_bid=second_highest_bids,
        payment=payments,
        payoffs=payoffs,
        revenue=payments.copy(),
        slot_assignment=slot_assignment,
        assigned_ctr=assigned_ctr,
        payment_per_click=payment_per_click,
        expected_payments=expected_payments,
        social_welfare=social_welfare,
    )
