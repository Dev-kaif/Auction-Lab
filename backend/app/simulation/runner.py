"""Orchestrates experiments. Valuations are generated ONCE per seed and reused for every
(profile, mechanism) pair so comparisons are paired on identical scenarios."""
from __future__ import annotations

import secrets
from typing import Any, Sequence

import numpy as np

from app.analytics.metrics import DEFINITIONS, summarize
from app.auctions.models import ADVERTISERS, AuctionInputError, MAX_VALUE, Mechanism, validate_vector
from app.auctions.strategies import MAX_ALPHA
from .engine import bids_from_alphas, parse_alphas, run_batch
from .valuations import generate_uniform_valuations

MAX_AUCTIONS = 10_000
MAX_PROFILES = 8
HIST_BINS = 20


def resolve_mechanisms(m: str) -> list[Mechanism]:
    if m == "both":
        return [Mechanism.FIRST_PRICE, Mechanism.SECOND_PRICE]
    return [Mechanism(m)]


def _validate_n(n: Any, cap: int = MAX_AUCTIONS) -> int:
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or not 1 <= n <= cap:
        raise AuctionInputError(f"n_auctions must be an integer between 1 and {cap}")
    return int(n)


def _seed(seed: int | None) -> tuple[int, bool]:
    if seed is None:
        return secrets.randbelow(2**31), True
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**31:
        raise AuctionInputError("seed must be an integer between 0 and 2147483647")
    return seed, False


def make_valuations(n: int, mode: str, low: float, high: float, fixed: Sequence[float] | None, seed: int) -> np.ndarray:
    if mode == "fixed":
        if fixed is None:
            raise AuctionInputError("fixed_values is required when valuation mode is 'fixed'")
        row = np.array([float(x) for x in validate_vector(fixed, "fixed_values")])
        return np.tile(row, (n, 1))
    if mode != "random":
        raise AuctionInputError("valuation mode must be 'random' or 'fixed'")
    return np.round(generate_uniform_valuations(n, low, high, seed), 2)  # paise grid, like the exact engine


def run_experiment(*, n_auctions: int, mechanism: str, mode: str, low: float, high: float,
                   fixed_values: Sequence[float] | None, seed: int | None,
                   profiles: Sequence[dict]) -> dict:
    n = _validate_n(n_auctions)
    if not 1 <= len(profiles) <= MAX_PROFILES:
        raise AuctionInputError(f"provide between 1 and {MAX_PROFILES} strategy profiles")
    labels = [p["label"] for p in profiles]
    if len(set(labels)) != len(labels):
        raise AuctionInputError("strategy profile labels must be unique")
    parsed = [(p["label"], parse_alphas(p["alphas"])) for p in profiles]
    mechs = resolve_mechanisms(mechanism)
    used_seed, generated = _seed(seed)
    vals = make_valuations(n, mode, low, high, fixed_values, used_seed)

    runs = []
    for label, alphas in parsed:
        bids = bids_from_alphas(vals, alphas)
        for mech in mechs:
            runs.append((label, alphas, mech, bids, run_batch(vals, bids, mech)))

    all_rev = np.concatenate([r[4].revenue for r in runs])
    lo, hi = float(all_rev.min()), float(all_rev.max())
    edges = np.linspace(lo, hi if hi > lo else lo + 1.0, HIST_BINS + 1)  # shared edges: distributions comparable

    notes = []
    if mode == "fixed":
        notes.append("Fixed valuations are deterministic: every auction repeats the same scenario, so results are "
                     "identical across auctions and the seed has no effect.")
    results = [{"profile_label": label, "alphas": [float(a) for a in alphas], "mechanism": mech.value,
                **summarize(vals, bids, batch, edges)} for label, alphas, mech, bids, batch in runs]
    return {
        "n_auctions": n, "seed": used_seed, "seed_was_generated": generated,
        "mechanisms": [m.value for m in mechs],
        "valuation": {"mode": mode, "low": low if mode == "random" else None, "high": high if mode == "random" else None,
                      "distribution": "uniform" if mode == "random" else "fixed",
                      "fixed_values": list(map(float, fixed_values)) if mode == "fixed" else None},
        "notes": notes, "definitions": DEFINITIONS, "results": results,
    }


def default_sweep_alphas() -> list[float]:
    return [round(float(a), 2) for a in np.arange(0.10, float(MAX_ALPHA) + 1e-9, 0.05)]


def run_sweep(*, n_auctions: int, mechanism: str, low: float, high: float, seed: int | None,
              mode: str = "all", deviator: str = "A", others_alpha: float = 1.0,
              alphas: Sequence[float] | None = None, max_n: int = MAX_AUCTIONS) -> dict:
    """Vary one alpha over a grid on shared valuations. mode='all': everyone uses alpha.
    mode='deviator': one advertiser uses alpha while the others use others_alpha."""
    n = _validate_n(n_auctions, max_n)
    if mode not in ("all", "deviator"):
        raise AuctionInputError("sweep mode must be 'all' or 'deviator'")
    if deviator not in ADVERTISERS:
        raise AuctionInputError("deviator must be one of A, B, C, D")
    grid = list(alphas) if alphas is not None else default_sweep_alphas()
    if not 1 <= len(grid) <= 60:
        raise AuctionInputError("provide between 1 and 60 alpha values")
    others = float(parse_alphas([others_alpha] * 4)[0])
    used_seed, generated = _seed(seed)
    vals = make_valuations(n, "random", low, high, None, used_seed)
    d = ADVERTISERS.index(deviator)
    out: dict[str, list] = {}
    for mech in resolve_mechanisms(mechanism):
        pts = []
        for a in grid:
            a = float(parse_alphas([a] * 4)[0])
            vec = np.full(4, a) if mode == "all" else np.where(np.arange(4) == d, a, others)
            bids = bids_from_alphas(vals, vec)
            b = run_batch(vals, bids, mech)
            pts.append({"alpha": a, "mean_revenue": float(b.revenue.mean()),
                        "mean_payoff_per_advertiser": float(b.payoffs.mean()),
                        "deviator_mean_payoff": float(b.payoffs[:, d].mean()) if mode == "deviator" else None,
                        "deviator_win_rate": float((b.winner == d).mean()) if mode == "deviator" else None})
        out[mech.value] = pts
    return {"n_auctions": n, "seed": used_seed, "seed_was_generated": generated, "mode": mode,
            "deviator": deviator if mode == "deviator" else None, "others_alpha": others if mode == "deviator" else None,
            "valuation": {"mode": "random", "low": low, "high": high, "distribution": "uniform"}, "points": out}
