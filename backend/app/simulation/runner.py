"""Coordinate simulation batches, comparisons, and bidding-fraction sweeps."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from app.analytics.metrics import DEFINITIONS, summarize
from app.auctions.models import (
    ADVERTISERS,
    AuctionInputError,
    DEFAULT_CLICK_THROUGH_RATES,
    Mechanism,
    validate_vector,
    validate_click_through_rates,
)
from app.auctions.strategies import MAX_ALPHA
from app.simulation.engine import Batch, bids_from_alphas, parse_alphas, run_batch
from app.simulation.valuations import generate_uniform_valuations

MAX_AUCTIONS = 10_000
MAX_PROFILES = 8
HISTOGRAM_BINS = 20


@dataclass(frozen=True)
class CompletedProfileRun:
    """The raw outputs for one profile and one auction mechanism."""

    profile_label: str
    alphas: np.ndarray
    mechanism: Mechanism
    bids: np.ndarray
    batch: Batch


def resolve_mechanisms(choice: str) -> list[Mechanism]:
    """Expand the UI's `both` option into the two implemented mechanisms."""
    if choice == "both":
        return [Mechanism.FIRST_PRICE, Mechanism.SECOND_PRICE]
    if choice == "all":
        return list(Mechanism)
    return [Mechanism(choice)]


def _validate_auction_count(count: Any, maximum: int = MAX_AUCTIONS) -> int:
    if (
        isinstance(count, bool)
        or not isinstance(count, (int, np.integer))
        or not 1 <= count <= maximum
    ):
        raise AuctionInputError(
            f"n_auctions must be an integer between 1 and {maximum}"
        )
    return int(count)


def _resolve_seed(seed: int | None) -> tuple[int, bool]:
    """Choose the supplied seed or generate one, and report which occurred."""
    if seed is None:
        return secrets.randbelow(2**31), True
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**31:
        raise AuctionInputError("seed must be an integer between 0 and 2147483647")
    return seed, False


def make_valuations(
    auction_count: int,
    mode: str,
    low: float,
    high: float,
    fixed_values: Sequence[float] | None,
    seed: int,
) -> np.ndarray:
    """Build the `(auction_count, 4)` valuation matrix for one experiment."""
    if mode == "fixed":
        if fixed_values is None:
            raise AuctionInputError(
                "fixed_values is required when valuation mode is 'fixed'"
            )

        # Validate through the same money rules used by manual auctions, then
        # repeat the resulting four values for every simulated auction.
        validated_values = validate_vector(fixed_values, "fixed_values")
        fixed_row = np.array([float(value) for value in validated_values])
        return np.tile(fixed_row, (auction_count, 1))

    if mode != "random":
        raise AuctionInputError("valuation mode must be 'random' or 'fixed'")

    generated = generate_uniform_valuations(auction_count, low, high, seed)
    return np.round(generated, 2)


def _validate_profiles(profiles: Sequence[dict[str, Any]]) -> list[tuple[str, np.ndarray]]:
    """Check profile count/labels and parse four bidding fractions per profile."""
    if not 1 <= len(profiles) <= MAX_PROFILES:
        raise AuctionInputError(
            f"provide between 1 and {MAX_PROFILES} strategy profiles"
        )

    labels = [profile["label"] for profile in profiles]
    if len(set(labels)) != len(labels):
        raise AuctionInputError("strategy profile labels must be unique")

    return [
        (profile["label"], parse_alphas(profile["alphas"]))
        for profile in profiles
    ]


def _run_profiles(
    valuations: np.ndarray,
    mechanisms: Sequence[Mechanism],
    profiles: Sequence[tuple[str, np.ndarray]],
    click_through_rates: Sequence[float],
) -> list[CompletedProfileRun]:
    """Run every selected profile/mechanism pair on one valuation matrix."""
    completed: list[CompletedProfileRun] = []
    for label, alphas in profiles:
        # Bids are the same across mechanisms; only the payment rule changes.
        bids = bids_from_alphas(valuations, alphas)
        for mechanism in mechanisms:
            batch = run_batch(valuations, bids, mechanism, click_through_rates)
            completed.append(
                CompletedProfileRun(label, alphas, mechanism, bids, batch)
            )
    return completed


def _shared_revenue_edges(runs: Sequence[CompletedProfileRun]) -> np.ndarray:
    """Use common histogram edges so every profile can be compared directly."""
    all_revenue = np.concatenate([run.batch.revenue for run in runs])
    lowest = float(all_revenue.min())
    highest = float(all_revenue.max())
    # NumPy needs a non-zero span even if every auction has identical revenue.
    upper_edge = highest if highest > lowest else lowest + 1.0
    return np.linspace(lowest, upper_edge, HISTOGRAM_BINS + 1)


def _result_blocks(
    valuations: np.ndarray,
    runs: Sequence[CompletedProfileRun],
    histogram_edges: np.ndarray,
) -> list[dict[str, Any]]:
    """Convert each raw batch into the documented aggregate result object."""
    return [
        {
            "profile_label": run.profile_label,
            "alphas": [float(alpha) for alpha in run.alphas],
            "mechanism": run.mechanism.value,
            **summarize(valuations, run.bids, run.batch, histogram_edges),
        }
        for run in runs
    ]


def run_experiment(
    *,
    n_auctions: int,
    mechanism: str,
    mode: str,
    low: float,
    high: float,
    fixed_values: Sequence[float] | None,
    seed: int | None,
    profiles: Sequence[dict[str, Any]],
    click_through_rates: Sequence[float] = DEFAULT_CLICK_THROUGH_RATES,
) -> dict[str, Any]:
    """Simulate the requested profile/mechanism combinations and summarize them.

    Valuations are generated once and shared across all combinations. This
    paired design makes differences reflect the strategy or mechanism rather
    than unrelated random valuation draws.
    """
    auction_count = _validate_auction_count(n_auctions)
    parsed_profiles = _validate_profiles(profiles)
    mechanisms = resolve_mechanisms(mechanism)
    used_seed, seed_was_generated = _resolve_seed(seed)
    valuations = make_valuations(
        auction_count,
        mode,
        low,
        high,
        fixed_values,
        used_seed,
    )

    ctrs = validate_click_through_rates(click_through_rates)
    completed_runs = _run_profiles(valuations, mechanisms, parsed_profiles, ctrs)
    histogram_edges = _shared_revenue_edges(completed_runs)
    result_blocks = _result_blocks(valuations, completed_runs, histogram_edges)

    notes: list[str] = []
    if mode == "fixed":
        notes.append(
            "Fixed valuations are deterministic: every auction repeats the same "
            "scenario, so results are identical across auctions and the seed "
            "has no effect."
        )

    valuation_settings: dict[str, Any] = {
        "mode": mode,
        "low": low if mode == "random" else None,
        "high": high if mode == "random" else None,
        "distribution": "uniform" if mode == "random" else "fixed",
        "fixed_values": list(map(float, fixed_values)) if mode == "fixed" else None,
    }
    return {
        "n_auctions": auction_count,
        "seed": used_seed,
        "seed_was_generated": seed_was_generated,
        "mechanisms": [item.value for item in mechanisms],
        "click_through_rates": list(ctrs) if any(m in (Mechanism.GSP, Mechanism.VCG) for m in mechanisms) else None,
        "valuation": valuation_settings,
        "notes": notes,
        "definitions": DEFINITIONS,
        "results": result_blocks,
    }


def default_sweep_alphas() -> list[float]:
    """Return the standard sweep grid from 0.10 through the maximum fraction."""
    return [
        round(float(alpha), 2)
        for alpha in np.arange(0.10, float(MAX_ALPHA) + 1e-9, 0.05)
    ]


def run_sweep(
    *,
    n_auctions: int,
    mechanism: str,
    low: float,
    high: float,
    seed: int | None,
    mode: str = "all",
    deviator: str = "A",
    others_alpha: float = 1.0,
    alphas: Sequence[float] | None = None,
    max_n: int = MAX_AUCTIONS,
    click_through_rates: Sequence[float] = DEFAULT_CLICK_THROUGH_RATES,
) -> dict[str, Any]:
    """Measure outcomes as one or all advertisers change their bid fraction.

    In `all` mode everyone uses the tested fraction. In `deviator` mode only
    the named advertiser changes fraction; the remaining three use
    `others_alpha`. Every point and mechanism shares the same valuations.
    """
    auction_count = _validate_auction_count(n_auctions, max_n)
    ctrs = validate_click_through_rates(click_through_rates)
    if mode not in ("all", "deviator"):
        raise AuctionInputError("sweep mode must be 'all' or 'deviator'")
    if deviator not in ADVERTISERS:
        raise AuctionInputError("deviator must be one of A, B, C, D")

    alpha_grid = list(alphas) if alphas is not None else default_sweep_alphas()
    if not 1 <= len(alpha_grid) <= 60:
        raise AuctionInputError("provide between 1 and 60 alpha values")

    reference_alpha = float(parse_alphas([others_alpha] * 4)[0])
    used_seed, seed_was_generated = _resolve_seed(seed)
    valuations = make_valuations(
        auction_count,
        "random",
        low,
        high,
        None,
        used_seed,
    )
    deviator_index = ADVERTISERS.index(deviator)

    points_by_mechanism: dict[str, list[dict[str, Any]]] = {}
    for auction_mechanism in resolve_mechanisms(mechanism):
        mechanism_points = []
        for raw_alpha in alpha_grid:
            alpha = float(parse_alphas([raw_alpha] * 4)[0])
            if mode == "all":
                fractions = np.full(4, alpha)
            else:
                fractions = np.where(
                    np.arange(4) == deviator_index,
                    alpha,
                    reference_alpha,
                )

            bids = bids_from_alphas(valuations, fractions)
            batch = run_batch(valuations, bids, auction_mechanism, ctrs)
            mechanism_points.append(
                {
                    "alpha": alpha,
                    "mean_revenue": float(batch.revenue.mean()),
                    "mean_payoff_per_advertiser": float(batch.payoffs.mean()),
                    "deviator_mean_payoff": (
                        float(batch.payoffs[:, deviator_index].mean())
                        if mode == "deviator"
                        else None
                    ),
                    "deviator_win_rate": (
                        float((batch.slot_assignment[:, deviator_index] > 0).mean())
                        if mode == "deviator"
                        else None
                    ),
                }
            )
        points_by_mechanism[auction_mechanism.value] = mechanism_points

    return {
        "n_auctions": auction_count,
        "seed": used_seed,
        "seed_was_generated": seed_was_generated,
        "mode": mode,
        "deviator": deviator if mode == "deviator" else None,
        "others_alpha": reference_alpha if mode == "deviator" else None,
        "valuation": {
            "mode": "random",
            "low": low,
            "high": high,
            "distribution": "uniform",
        },
        "click_through_rates": list(ctrs)
        if any(Mechanism(key) in (Mechanism.GSP, Mechanism.VCG) for key in points_by_mechanism)
        else None,
        "points": points_by_mechanism,
    }
