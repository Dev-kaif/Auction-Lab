from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from .winner import runner_up_bid


def second_price_payment(bids: Sequence[Decimal], winner: int) -> Decimal:
    """Charge the highest bid among losing advertisers: p_w = max(j≠w) b_j.

    Looking only at losing bids matters when tied top bids exist: the winner
    pays that same top amount because another advertiser submitted it too.
    """
    return runner_up_bid(bids, winner)
