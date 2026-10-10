from __future__ import annotations

from decimal import Decimal
from typing import Sequence


def first_price_payment(bids: Sequence[Decimal], winner: int) -> Decimal:
    """Winner pays their own submitted bid: p_w = b_w."""
    return bids[winner]
