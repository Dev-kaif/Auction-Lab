"""Calculate the aggregate values returned for each simulated result group."""

from __future__ import annotations

import numpy as np

from app.auctions.models import ADVERTISERS
from app.simulation.engine import Batch

# Keep denominators explicit: the API returns proportions and rupee amounts,
# while the frontend decides how to display them (for example, as percents).
DEFINITIONS = {
    "revenue": "Platform revenue per auction = the winner's payment. Mean/median/std over all completed auctions.",
    "se": "Standard error of the mean revenue = sample std / sqrt(number of auctions): Monte Carlo uncertainty of the mean.",
    "win_rate": "Auctions won by the advertiser / total completed auctions.",
    "avg_payoff": "Advertiser's total payoff / total completed auctions (losing auctions count as 0).",
    "avg_winner_payoff": "Sum of winners' payoffs / total completed auctions (exactly one winner per auction).",
    "avg_bidder_surplus": "Mean payoff over all advertiser-auction pairs = total payoff / (4 x auctions). Equals avg winner payoff / 4.",
    "highest_value_win_rate": "Auctions won by an advertiser holding the highest valuation / total completed auctions.",
    "overbid_rate": "Auctions in which at least one advertiser bid above their valuation / total completed auctions.",
    "negative_winner_payoff_rate": "Auctions whose winner's payoff is negative / total completed auctions.",
    "avg_winning_bid": "Mean of the highest submitted bid over all completed auctions.",
    "avg_winning_payment": "Mean price paid by the winner over all completed auctions (equals mean revenue).",
}


def revenue_stats(revenue: np.ndarray) -> dict[str, float]:
    """Summarize auction revenue; use zero deviation when there is one sample."""
    auction_count = len(revenue)
    sample_std_dev = float(np.std(revenue, ddof=1)) if auction_count > 1 else 0.0
    standard_error = sample_std_dev / float(np.sqrt(auction_count))

    return {
        "mean": float(revenue.mean()),
        "median": float(np.median(revenue)),
        "std": sample_std_dev,
        "se": standard_error,
        "min": float(revenue.min()),
        "max": float(revenue.max()),
    }


def revenue_histogram(
    revenue: np.ndarray,
    shared_edges: np.ndarray,
) -> dict[str, list]:
    """Count auction revenues in the bins shared by all experiment groups."""
    counts, _ = np.histogram(revenue, bins=shared_edges)
    return {
        "edges": [float(edge) for edge in shared_edges],
        "counts": [int(count) for count in counts],
    }


def revenue_convergence(
    revenue: np.ndarray,
    maximum_checkpoints: int = 50,
) -> dict[str, list]:
    """Return running mean revenue at evenly spaced auction-count checkpoints."""
    auction_count = len(revenue)
    checkpoint_counts = np.unique(
        np.linspace(1, auction_count, min(auction_count, maximum_checkpoints)).astype(int)
    )
    running_means = np.cumsum(revenue) / np.arange(1, auction_count + 1)

    return {
        "n": [int(count) for count in checkpoint_counts],
        "mean": [float(running_means[count - 1]) for count in checkpoint_counts],
    }


def summarize(
    valuations: np.ndarray,
    bids: np.ndarray,
    batch: Batch,
    shared_histogram_edges: np.ndarray,
) -> dict:
    """Calculate result metrics for one strategy-profile/mechanism pair."""
    auction_count = valuations.shape[0]
    auction_rows = np.arange(auction_count)

    # Only the winner has a non-zero payoff, so summing the four columns gives
    # each auction's winner payoff. Losses remain zero in the advertiser array.
    winner_payoff_per_auction = batch.payoffs.sum(axis=1)
    wins_per_advertiser = np.bincount(
        batch.winner,
        minlength=len(ADVERTISERS),
    )
    win_rate_by_advertiser = wins_per_advertiser / auction_count

    return {
        "n_auctions": auction_count,
        "revenue": revenue_stats(batch.revenue),
        "avg_winning_bid": float(batch.winning_bid.mean()),
        "avg_winning_payment": float(batch.payment.mean()),
        "avg_winner_payoff": float(winner_payoff_per_auction.mean()),
        # The mean covers every advertiser-auction pair, including zero payoffs.
        "avg_bidder_surplus": float(batch.payoffs.mean()),
        "highest_value_win_rate": float(
            (
                valuations[auction_rows, batch.winner]
                >= valuations.max(axis=1)
            ).mean()
        ),
        "overbid_rate": float((bids > valuations).any(axis=1).mean()),
        "negative_winner_payoff_rate": float(
            (winner_payoff_per_auction < 0).mean()
        ),
        "win_rate": {
            advertiser: float(win_rate_by_advertiser[index])
            for index, advertiser in enumerate(ADVERTISERS)
        },
        "avg_payoff": {
            advertiser: float(batch.payoffs[:, index].mean())
            for index, advertiser in enumerate(ADVERTISERS)
        },
        "revenue_histogram": revenue_histogram(
            batch.revenue,
            shared_histogram_edges,
        ),
        "convergence": revenue_convergence(batch.revenue),
    }
