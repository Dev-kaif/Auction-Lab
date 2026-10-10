"""Bidding strategies: b_i = alpha * v_i (truthful is alpha = 1)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from .models import AuctionInputError, N_ADVERTISERS, to_money

MAX_ALPHA = Decimal("1.5")


def validate_alpha(alpha: object) -> Decimal:
    if isinstance(alpha, bool):
        raise AuctionInputError("alpha must be a number")
    try:
        a = Decimal(str(alpha))
    except Exception as exc:
        raise AuctionInputError(f"alpha is not a valid number: {alpha!r}") from exc
    if not a.is_finite():
        raise AuctionInputError("alpha must be finite")
    if a < 0 or a > MAX_ALPHA:
        raise AuctionInputError(f"alpha must be between 0 and {MAX_ALPHA}, got {alpha}")
    return a


@dataclass(frozen=True)
class FixedFraction:
    """Bid a fixed fraction alpha of the valuation. alpha > 1 is overbidding."""
    alpha: Decimal

    def __init__(self, alpha: object):
        object.__setattr__(self, "alpha", validate_alpha(alpha))

    @property
    def name(self) -> str:
        return "truthful" if self.alpha == 1 else f"fixed_fraction_{self.alpha.normalize():f}"

    def bid(self, valuation: object) -> Decimal:
        return to_money(Decimal(str(valuation)) * self.alpha, "bid")


def Truthful() -> FixedFraction:  # noqa: N802 - reads like a class
    return FixedFraction(1)


def bids_from_strategies(valuations: Sequence[object], strategies: Sequence[FixedFraction]) -> list[Decimal]:
    if len(valuations) != N_ADVERTISERS or len(strategies) != N_ADVERTISERS:
        raise AuctionInputError(f"need exactly {N_ADVERTISERS} valuations and strategies")
    return [s.bid(to_money(v, "valuation")) for v, s in zip(valuations, strategies)]
