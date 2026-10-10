"""Reproducible valuation scenario generation."""
from __future__ import annotations

import numpy as np

from app.auctions.models import AuctionInputError, MAX_VALUE, N_ADVERTISERS


def generate_uniform_valuations(n_auctions: int, low: float, high: float, seed: int | None) -> np.ndarray:
    """(n_auctions, 4) i.i.d. Uniform[low, high] valuations from a seeded generator.

    Generate once per seed and reuse across mechanisms/strategies (paired comparison).
    """
    if not isinstance(n_auctions, (int, np.integer)) or isinstance(n_auctions, bool) or n_auctions < 1:
        raise AuctionInputError("n_auctions must be a positive integer")
    if not (np.isfinite(low) and np.isfinite(high)) or low < 0 or high <= low or high > float(MAX_VALUE):
        raise AuctionInputError("require 0 <= low < high <= max value, all finite")
    rng = np.random.default_rng(seed)
    return rng.uniform(low, high, size=(int(n_auctions), N_ADVERTISERS))
