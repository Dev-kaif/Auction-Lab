"""Domain types and input validation for the four-advertiser auction.

All monetary values in the exact engine are Decimal rounded to 2 places (paise),
so displayed currency never shows floating-point artifacts.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

ADVERTISERS: tuple[str, ...] = ("A", "B", "C", "D")
N_ADVERTISERS = len(ADVERTISERS)
MAX_VALUE = Decimal("1000000")  # maximum configurable valuation or bid (INR)
CENT = Decimal("0.01")


class Mechanism(str, Enum):
    FIRST_PRICE = "first_price"
    SECOND_PRICE = "second_price"


class AuctionInputError(ValueError):
    """Raised when valuations, bids or parameters are invalid."""


def to_money(value: object, name: str = "value") -> Decimal:
    """Validate and convert a number to a Decimal rounded to 2 places."""
    if isinstance(value, bool):
        raise AuctionInputError(f"{name} must be a number, got a boolean")
    try:
        if isinstance(value, float):
            if not math.isfinite(value):
                raise AuctionInputError(f"{name} must be finite, got {value}")
            d = Decimal(str(value))
        else:
            d = Decimal(value)  # type: ignore[arg-type]
    except AuctionInputError:
        raise
    except Exception as exc:
        raise AuctionInputError(f"{name} is not a valid number: {value!r}") from exc
    if not d.is_finite():
        raise AuctionInputError(f"{name} must be finite, got {value}")
    if d < 0:
        raise AuctionInputError(f"{name} must be non-negative, got {value}")
    if d > MAX_VALUE:
        raise AuctionInputError(f"{name} must be at most {MAX_VALUE}, got {value}")
    return d.quantize(CENT, rounding=ROUND_HALF_UP)


def validate_vector(values: object, name: str) -> tuple[Decimal, ...]:
    """Validate a length-4 sequence of valuations or bids."""
    try:
        seq = list(values)  # type: ignore[call-overload]
    except TypeError as exc:
        raise AuctionInputError(f"{name} must be a sequence of {N_ADVERTISERS} numbers") from exc
    if len(seq) != N_ADVERTISERS:
        raise AuctionInputError(f"{name} must contain exactly {N_ADVERTISERS} values, got {len(seq)}")
    return tuple(to_money(v, f"{name}[{ADVERTISERS[i]}]") for i, v in enumerate(seq))


@dataclass(frozen=True)
class AdvertiserResult:
    advertiser: str
    valuation: Decimal
    bid: Decimal
    rank: int  # 1 = highest bid; ties ranked by advertiser index
    won: bool
    payment: Decimal
    payoff: Decimal
    overbid: bool  # bid > valuation


@dataclass(frozen=True)
class AuctionResult:
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
    payoff_sign: str  # "positive" | "zero" | "negative"
    any_overbid: bool
    tie_for_highest_bid: bool
    tied_bidders: tuple[str, ...]
    tie_break_rule: str = "Ties among the highest bids go to the lowest advertiser index (A before B before C before D)."
