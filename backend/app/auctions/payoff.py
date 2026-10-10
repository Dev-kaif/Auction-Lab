from __future__ import annotations

from decimal import Decimal
from typing import Sequence


def compute_payoffs(valuations: Sequence[Decimal], payments: Sequence[Decimal], winner: int) -> list[Decimal]:
    """Apply quasilinear utility to the winner; losing bidders get zero."""
    # Utility uses true valuation, not the submitted bid: u_w = v_w - p_w.
    # There is only one allocated slot, so every other bidder has payoff 0.
    return [
        valuations[index] - payments[index]
        if index == winner
        else Decimal("0.00")
        for index in range(len(valuations))
    ]


def platform_revenue(payments: Sequence[Decimal]) -> Decimal:
    """Add payments across bidders; with one slot, only the winner pays."""
    return sum(payments, Decimal("0.00"))
