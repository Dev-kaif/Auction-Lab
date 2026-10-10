"""Core domain types and input validation for the four-advertiser auction."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

ADVERTISERS: tuple[str, ...] = ("A", "B", "C", "D")
N_ADVERTISERS = len(ADVERTISERS)
MAX_VALUE = Decimal("1000000")
CENT = Decimal("0.01")


class Mechanism(str, Enum):
    """Payment rule used after the highest bid wins."""

    FIRST_PRICE = "first_price"
    SECOND_PRICE = "second_price"


class AuctionInputError(ValueError):
    """Raised when a domain input is outside the auction's valid range."""


def to_money(value: object, name: str = "value") -> Decimal:
    """Validate a monetary amount and round it to paise, half up."""
    if isinstance(value, bool):
        raise AuctionInputError(f"{name} must be a number, got a boolean")

    try:
        if isinstance(value, float):
            if not math.isfinite(value):
                raise AuctionInputError(f"{name} must be finite, got {value}")
            amount = Decimal(str(value))
        else:
            amount = Decimal(value)  # type: ignore[arg-type]
    except AuctionInputError:
        raise
    except Exception as exc:
        raise AuctionInputError(f"{name} is not a valid number: {value!r}") from exc

    if not amount.is_finite():
        raise AuctionInputError(f"{name} must be finite, got {value}")
    if amount < 0:
        raise AuctionInputError(f"{name} must be non-negative, got {value}")
    if amount > MAX_VALUE:
        raise AuctionInputError(f"{name} must be at most {MAX_VALUE}, got {value}")

    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def validate_vector(values: object, name: str) -> tuple[Decimal, ...]:
    """Convert a four-item A–D list to validated Decimal amounts."""
    try:
        items = list(values)  # type: ignore[call-overload]
    except TypeError as exc:
        raise AuctionInputError(
            f"{name} must be a sequence of {N_ADVERTISERS} numbers"
        ) from exc

    if len(items) != N_ADVERTISERS:
        raise AuctionInputError(
            f"{name} must contain exactly {N_ADVERTISERS} values, got {len(items)}"
        )

    return tuple(
        to_money(value, f"{name}[{ADVERTISERS[index]}]")
        for index, value in enumerate(items)
    )


@dataclass(frozen=True)
class AdvertiserResult:
    """One advertiser's input and calculated outcome for a manual auction."""

    advertiser: str
    valuation: Decimal
    bid: Decimal
    rank: int  # 1 is the top bid; equal bids follow A, B, C, D order.
    won: bool
    payment: Decimal
    payoff: Decimal
    overbid: bool


@dataclass(frozen=True)
class AuctionResult:
    """Complete domain result for one single-slot auction."""

    mechanism: Mechanism
    results: tuple[AdvertiserResult, ...]
    winner_index: int
    winner: str
    winning_bid: Decimal
    runner_up_bid: Decimal
    payment: Decimal
    winner_payoff: Decimal
    revenue: Decimal
    highest_valuation: Decimal
    highest_valued_won: bool
    winner_surplus: Decimal
    payoff_sign: str
    any_overbid: bool
    tie_for_highest_bid: bool
    tied_bidders: tuple[str, ...]
    tie_break_rule: str = (
        "Ties among the highest bids go to the lowest advertiser index "
        "(A before B before C before D)."
    )
