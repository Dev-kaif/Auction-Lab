"""Allocation and payment calculations for position-based GSP and VCG auctions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from app.auctions.models import Mechanism, validate_click_through_rates
from app.auctions.winner import ranking

CENT = Decimal("0.01")


def _round_money(amount: Decimal) -> Decimal:
    """Use the same paise-level half-up rounding as the single-slot engine."""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class SlotOutcome:
    """Per-advertiser allocation and payment arrays in advertiser order."""

    slots: tuple[int | None, ...]  # one-based slot number; None means unallocated
    ctrs: tuple[float, ...]
    price_per_click: tuple[Decimal, ...]
    expected_payment: tuple[Decimal, ...]  # rupees per impression
    expected_utility: tuple[Decimal, ...]  # rupees per impression
    social_welfare: Decimal


def allocate_slots(
    valuations: Sequence[Decimal],
    bids: Sequence[Decimal],
    mechanism: Mechanism,
    click_through_rates: Sequence[float],
) -> SlotOutcome:
    """Rank bids and calculate GSP prices or VCG externalities.

    VCG's externality is measured in expected rupees per impression. Its
    per-click equivalent is that amount divided by the assigned slot CTR.
    """
    rates = validate_click_through_rates(click_through_rates)
    order = ranking(bids)
    assigned = order[: len(rates)]
    slots: list[int | None] = [None] * len(bids)
    ctr_by_advertiser = [0.0] * len(bids)
    price = [Decimal("0.00")] * len(bids)
    expected_payment = [Decimal("0.00")] * len(bids)
    expected_utility = [Decimal("0.00")] * len(bids)
    welfare = Decimal("0.00")

    for slot_index, advertiser_index in enumerate(assigned):
        ctr = rates[slot_index]
        slots[advertiser_index] = slot_index + 1
        ctr_by_advertiser[advertiser_index] = ctr
        welfare += (valuations[advertiser_index] * Decimal(str(ctr)))

        if mechanism is Mechanism.GSP:
            next_bid = bids[order[slot_index + 1]] if slot_index + 1 < len(order) else Decimal("0.00")
            price[advertiser_index] = next_bid
            expected_payment[advertiser_index] = _round_money(next_bid * Decimal(str(ctr)))
        elif mechanism is Mechanism.VCG:
            # Others' best achievable bid-weighted welfare without this bidder.
            others = [index for index in order if index != advertiser_index]
            without_i = sum(
                (Decimal(str(rates[s])) * bids[others[s]] for s in range(min(len(rates), len(others)))),
                Decimal("0.00"),
            )
            # Welfare for the other bidders in the actual allocation, excluding i.
            with_i_others = sum(
                (Decimal(str(rates[s])) * bids[index]
                 for s, index in enumerate(assigned) if index != advertiser_index),
                Decimal("0.00"),
            )
            externality = max(Decimal("0.00"), without_i - with_i_others)
            expected_payment[advertiser_index] = _round_money(externality)
            price[advertiser_index] = (
                _round_money(expected_payment[advertiser_index] / Decimal(str(ctr)))
                if ctr > 0 else Decimal("0.00")
            )

        utility = (
            Decimal(str(ctr)) * valuations[advertiser_index]
            - expected_payment[advertiser_index]
        )
        expected_utility[advertiser_index] = _round_money(utility)

    return SlotOutcome(
        slots=tuple(slots), ctrs=tuple(ctr_by_advertiser),
        price_per_click=tuple(price), expected_payment=tuple(expected_payment),
        expected_utility=tuple(expected_utility), social_welfare=_round_money(welfare),
    )
