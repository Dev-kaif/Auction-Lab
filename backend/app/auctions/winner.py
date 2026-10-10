"""Winner determination with deterministic tie-breaking."""
from __future__ import annotations

from decimal import Decimal
from typing import Sequence


def ranking(bids: Sequence[Decimal]) -> list[int]:
    """Return bidder indices ordered by amount, then by A–D priority."""
    # Negating each bid makes Python's ascending sort put the largest bid first.
    # The second key keeps the earlier advertiser first when bids are equal.
    return sorted(range(len(bids)), key=lambda index: (-bids[index], index))


def determine_winner(bids: Sequence[Decimal]) -> int:
    """Return the top-ranked bidder's index (A wins an exact top-bid tie)."""
    return ranking(bids)[0]


def runner_up_bid(bids: Sequence[Decimal], winner: int) -> Decimal:
    """Find the highest losing bid, including an equal bid in a top tie."""
    losing_bids = [bid for index, bid in enumerate(bids) if index != winner]
    return max(losing_bids)
