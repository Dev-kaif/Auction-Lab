from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from .winner import runner_up_bid


def second_price_payment(bids: Sequence[Decimal], winner: int) -> Decimal:
    """Winner pays the highest bid among the others: p_w = max_{j != w} b_j."""
    return runner_up_bid(bids, winner)
