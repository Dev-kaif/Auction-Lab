"""Simple bidding rules for the manual-auction engine."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from app.auctions.models import AuctionInputError, N_ADVERTISERS, to_money

MAX_ALPHA = Decimal("1.5")


def validate_alpha(alpha: object) -> Decimal:
    """Convert a bidding fraction to Decimal and require 0 ≤ alpha ≤ 1.5."""
    if isinstance(alpha, bool):
        raise AuctionInputError("alpha must be a number")

    try:
        fraction = Decimal(str(alpha))
    except Exception as exc:
        raise AuctionInputError(
            f"alpha is not a valid number: {alpha!r}"
        ) from exc

    if not fraction.is_finite():
        raise AuctionInputError("alpha must be finite")
    if fraction < 0 or fraction > MAX_ALPHA:
        raise AuctionInputError(
            f"alpha must be between 0 and {MAX_ALPHA}, got {alpha}"
        )
    return fraction


@dataclass(frozen=True)
class FixedFraction:
    """Bid a fixed proportion of valuation; alpha above 1 means overbidding."""

    alpha: Decimal

    def __init__(self, alpha: object):
        object.__setattr__(self, "alpha", validate_alpha(alpha))

    @property
    def name(self) -> str:
        if self.alpha == 1:
            return "truthful"
        return f"fixed_fraction_{self.alpha.normalize():f}"

    def bid(self, valuation: object) -> Decimal:
        raw_value = Decimal(str(valuation))
        return to_money(raw_value * self.alpha, "bid")


def Truthful() -> FixedFraction:  # noqa: N802 - reads like a class
    """Create the truthful strategy, which submits the valuation as the bid."""
    return FixedFraction(1)


def bids_from_strategies(
    valuations: Sequence[object],
    strategies: Sequence[FixedFraction],
) -> list[Decimal]:
    """Apply one strategy per advertiser and return bids ordered A through D."""
    if len(valuations) != N_ADVERTISERS or len(strategies) != N_ADVERTISERS:
        raise AuctionInputError(
            f"need exactly {N_ADVERTISERS} valuations and strategies"
        )

    return [
        strategy.bid(valuation)
        for valuation, strategy in zip(valuations, strategies)
    ]
