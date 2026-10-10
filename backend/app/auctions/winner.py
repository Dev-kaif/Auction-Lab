"""Winner determination with deterministic tie-breaking."""
from __future__ import annotations

from decimal import Decimal
from typing import Sequence


def ranking(bids: Sequence[Decimal]) -> list[int]:
    """Advertiser indices ordered by bid descending, ties by lowest index."""
    return sorted(range(len(bids)), key=lambda i: (-bids[i], i))


def determine_winner(bids: Sequence[Decimal]) -> int:
    """argmax of bids; ties broken toward the lowest index."""
    return ranking(bids)[0]


def runner_up_bid(bids: Sequence[Decimal], winner: int) -> Decimal:
    """Highest bid among everyone except the winner (equals the winning bid on a tie)."""
    return max(b for j, b in enumerate(bids) if j != winner)
