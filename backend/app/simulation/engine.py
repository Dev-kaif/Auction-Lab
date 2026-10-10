"""Fast NumPy auction engine for evaluating many auctions at once."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.auctions.models import AuctionInputError, Mechanism, N_ADVERTISERS
from app.auctions.strategies import validate_alpha


@dataclass(frozen=True)
class Batch:
    """Auction outcomes stored as arrays, one row per simulated auction."""

    winner: np.ndarray  # (n,) winner index: A=0, B=1, C=2, D=3
    winning_bid: np.ndarray  # (n,) highest bid in each auction
    runner_up_bid: np.ndarray  # (n,) highest bid excluding the winner
    payment: np.ndarray  # (n,) winner's payment under the selected mechanism
    payoffs: np.ndarray  # (n, 4) payoff per advertiser; losers receive zero
    revenue: np.ndarray  # (n,) total platform payment (one winner per auction)


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

    if selected_mechanism is Mechanism.FIRST_PRICE:
        payments = highest_bids
    else:
        # When top bids tie, the runner-up is also the top bid.
        payments = second_highest_bids

    payoffs = np.zeros_like(valuations, dtype=float)
    payoffs[auction_rows, winner_indices] = (
        valuations[auction_rows, winner_indices] - payments
    )

    return Batch(
        winner=winner_indices,
        winning_bid=highest_bids,
        runner_up_bid=second_highest_bids,
        payment=payments,
        payoffs=payoffs,
        revenue=payments.copy(),
    )
