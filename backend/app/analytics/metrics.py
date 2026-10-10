"""Calculate the aggregate values returned for each simulated result group."""

from __future__ import annotations

import numpy as np

from app.auctions.models import ADVERTISERS
from app.simulation.engine import Batch

# Keep denominators explicit: the API returns proportions and rupee amounts,
# while the frontend decides how to display them (for example, as percents).
DEFINITIONS = {
    "revenue": "Platform payment per auction (single-slot) or expected total payment per impression (multi-slot); mean/median/std over completed auctions.",
    "se": "Standard error of the mean revenue = sample std / sqrt(number of auctions): Monte Carlo uncertainty of the mean.",
    "win_rate": "Auctions in which the advertiser wins or receives any slot / total completed auctions. Multi-slot rates can sum above 1 across advertisers.",
    "avg_payoff": "Advertiser's total payoff or expected utility / total completed auctions (unallocated auctions count as 0).",
    "avg_winner_payoff": "Mean expected utility of the top-ranked advertiser / completed auctions. For single-slot auctions this is the winner's payoff.",
    "avg_total_expected_utility": "Sum of advertiser expected utilities / completed auctions; rupees per impression for multi-slot auctions.",
    "avg_bidder_surplus": "Mean utility over all four advertiser-auction pairs, including zeros for unallocated advertisers.",
    "highest_value_win_rate": "Auctions won by an advertiser holding the highest valuation / total completed auctions.",
    "overbid_rate": "Auctions in which at least one advertiser bid above their valuation / total completed auctions.",
    "negative_winner_payoff_rate": "Auctions whose winner's payoff is negative / total completed auctions.",
    "avg_winning_bid": "Mean of the highest submitted bid over all completed auctions.",
    "avg_winning_payment": "Mean platform payment over completed auctions/impressions (equals mean revenue; multi-slot payment sums across allocated advertisers).",
    "expected_utility": "Expected advertiser value minus expected payment, in rupees per impression; unallocated advertisers have zero utility.",
    "social_welfare": "Sum of allocated CTR × true value across advertisers, in rupees per impression.",
    "slot_win_rate": "Auctions in which an advertiser receives any slot / completed auctions; rates can sum above one across advertisers.",
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

    # Keep top-slot payoff distinct from the sum of utilities across every slot.
    total_utility_per_auction = batch.payoffs.sum(axis=1)
    top_ranked_utility = batch.payoffs[auction_rows, batch.winner]
    wins_per_advertiser = (batch.slot_assignment > 0).sum(axis=0)
    win_rate_by_advertiser = wins_per_advertiser / auction_count

    return {
        "n_auctions": auction_count,
        "revenue": revenue_stats(batch.revenue),
        "avg_winning_bid": float(batch.winning_bid.mean()),
        "avg_winning_payment": float(batch.payment.mean()),
        "avg_winner_payoff": float(top_ranked_utility.mean()),
        "avg_total_expected_utility": float(total_utility_per_auction.mean()),
        # The mean covers every advertiser-auction pair, including zero payoffs.
        "avg_bidder_surplus": float(batch.payoffs.mean()),
        "highest_value_win_rate": float(
            (
                ((valuations >= valuations.max(axis=1, keepdims=True))
                 & (batch.slot_assignment > 0)).any(axis=1)
            ).mean()
        ),
        "overbid_rate": float((bids > valuations).any(axis=1).mean()),
        "negative_winner_payoff_rate": float(
            (top_ranked_utility < 0).mean()
        ),
        "win_rate": {
            advertiser: float(win_rate_by_advertiser[index])
            for index, advertiser in enumerate(ADVERTISERS)
        },
        "avg_payoff": {
            advertiser: float(batch.payoffs[:, index].mean())
            for index, advertiser in enumerate(ADVERTISERS)
        },
        "avg_expected_utility": {
            advertiser: float(batch.payoffs[:, index].mean())
            for index, advertiser in enumerate(ADVERTISERS)
        },
        "average_click_through_rate": {
            advertiser: float(batch.assigned_ctr[:, index].mean())
            for index, advertiser in enumerate(ADVERTISERS)
        },
        "average_payment_per_click": {
            advertiser: float(batch.payment_per_click[:, index].mean())
            for index, advertiser in enumerate(ADVERTISERS)
        },
        "slot_win_rate": {
            advertiser: float(win_rate_by_advertiser[index])
            for index, advertiser in enumerate(ADVERTISERS)
        },
        "avg_social_welfare": float(batch.social_welfare.mean()),
        "avg_expected_payment": float(batch.revenue.mean()),
        "revenue_histogram": revenue_histogram(
            batch.revenue,
            shared_histogram_edges,
        ),
        "convergence": revenue_convergence(batch.revenue),
    }
