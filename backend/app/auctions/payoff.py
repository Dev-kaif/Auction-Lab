from __future__ import annotations

from decimal import Decimal
from typing import Sequence


def compute_payoffs(valuations: Sequence[Decimal], payments: Sequence[Decimal], winner: int) -> list[Decimal]:
    """u_i = v_i - p_i for the winner (true valuation, not bid); 0 for losers."""
    return [valuations[i] - payments[i] if i == winner else Decimal("0.00") for i in range(len(valuations))]


def platform_revenue(payments: Sequence[Decimal]) -> Decimal:
    """R = sum of all payments."""
    return sum(payments, Decimal("0.00"))
