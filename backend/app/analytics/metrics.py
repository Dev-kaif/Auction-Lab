"""Aggregate metrics for one (strategy profile, mechanism) simulation. Denominators are explicit."""
from __future__ import annotations

import numpy as np

from app.auctions.models import ADVERTISERS
from app.simulation.engine import Batch

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
    n = len(revenue)
    std = float(np.std(revenue, ddof=1)) if n > 1 else 0.0
    return {"mean": float(revenue.mean()), "median": float(np.median(revenue)), "std": std,
            "se": std / float(np.sqrt(n)), "min": float(revenue.min()), "max": float(revenue.max())}


def histogram(revenue: np.ndarray, edges: np.ndarray) -> dict[str, list]:
    counts, _ = np.histogram(revenue, bins=edges)
    return {"edges": [float(e) for e in edges], "counts": [int(c) for c in counts]}


def convergence(revenue: np.ndarray, points: int = 50) -> dict[str, list]:
    n = len(revenue)
    ns = np.unique(np.linspace(1, n, min(n, points)).astype(int))
    running = np.cumsum(revenue) / np.arange(1, n + 1)
    return {"n": [int(x) for x in ns], "mean": [float(running[x - 1]) for x in ns]}


def summarize(valuations: np.ndarray, bids: np.ndarray, batch: Batch, edges: np.ndarray) -> dict:
    n = valuations.shape[0]
    rows = np.arange(n)
    winner_payoff = batch.payoffs.sum(axis=1)
    win_rate = np.bincount(batch.winner, minlength=len(ADVERTISERS)) / n
    return {
        "n_auctions": n,
        "revenue": revenue_stats(batch.revenue),
        "avg_winning_bid": float(batch.winning_bid.mean()),
        "avg_winning_payment": float(batch.payment.mean()),
        "avg_winner_payoff": float(winner_payoff.mean()),
        "avg_bidder_surplus": float(batch.payoffs.mean()),
        "highest_value_win_rate": float((valuations[rows, batch.winner] >= valuations.max(axis=1)).mean()),
        "overbid_rate": float((bids > valuations).any(axis=1).mean()),
        "negative_winner_payoff_rate": float((winner_payoff < 0).mean()),
        "win_rate": {a: float(win_rate[i]) for i, a in enumerate(ADVERTISERS)},
        "avg_payoff": {a: float(batch.payoffs[:, i].mean()) for i, a in enumerate(ADVERTISERS)},
        "revenue_histogram": histogram(batch.revenue, edges),
        "convergence": convergence(batch.revenue),
    }
