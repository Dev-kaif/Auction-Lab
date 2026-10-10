"""Vectorized batch auction engine (NumPy). Mirrors app.auctions.engine rules exactly.

Valuations are rounded to paise (2 dp) and bids = round(alpha * v, 2), the same grid the exact
Decimal engine uses. Ties go to the lowest advertiser index because np.argmax returns the first max.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.auctions.models import AuctionInputError, Mechanism, N_ADVERTISERS
from app.auctions.strategies import validate_alpha


@dataclass(frozen=True)
class Batch:
    winner: np.ndarray        # (n,) winner index
    winning_bid: np.ndarray   # (n,)
    runner_up_bid: np.ndarray # (n,) highest bid among the others (== winning bid on a tie)
    payment: np.ndarray       # (n,)
    payoffs: np.ndarray       # (n, 4) v_i - p_i for the winner, 0 for losers
    revenue: np.ndarray       # (n,) sum of payments


def parse_alphas(alphas: object) -> np.ndarray:
    seq = list(alphas)  # type: ignore[call-overload]
    if len(seq) != N_ADVERTISERS:
        raise AuctionInputError(f"alphas must contain exactly {N_ADVERTISERS} values")
    return np.array([float(validate_alpha(a)) for a in seq])


def bids_from_alphas(valuations: np.ndarray, alphas: np.ndarray) -> np.ndarray:
    return np.round(valuations * alphas[None, :], 2)


def run_batch(valuations: np.ndarray, bids: np.ndarray, mechanism: Mechanism | str) -> Batch:
    mech = Mechanism(mechanism)
    if valuations.shape != bids.shape or valuations.ndim != 2 or valuations.shape[1] != N_ADVERTISERS:
        raise AuctionInputError("valuations and bids must both have shape (n_auctions, 4)")
    n = valuations.shape[0]
    rows = np.arange(n)
    winner = np.argmax(bids, axis=1)
    srt = np.sort(bids, axis=1)
    top, second = srt[:, -1], srt[:, -2]
    payment = top if mech is Mechanism.FIRST_PRICE else second
    payoffs = np.zeros_like(valuations, dtype=float)
    payoffs[rows, winner] = valuations[rows, winner] - payment
    return Batch(winner, top, second, payment, payoffs, payment.copy())
