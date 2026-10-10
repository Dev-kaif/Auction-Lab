"""Generate the explanation text from an actual AuctionResult (never hardcoded)."""

from __future__ import annotations

from decimal import Decimal

from .models import AuctionResult, Mechanism


def inr(x: Decimal) -> str:
    sign = "-" if x < 0 else ""
    return f"{sign}₹{abs(x):,.2f}"


def explain(r: AuctionResult) -> str:
    w = next(x for x in r.results if x.won)
    parts = [
        f"Advertiser {r.winner} submitted the highest bid of {inr(r.winning_bid)} and won."
    ]
    if r.tie_for_highest_bid:
        parts.append(
            f"Advertisers {', '.join(r.tied_bidders)} tied for the highest bid; "
            f"the tie-break rule (lowest index first) awarded the slot to {r.winner}."
        )
    if r.mechanism is Mechanism.FIRST_PRICE:
        parts.append(
            f"Under the first-price rule, {r.winner} pays their own bid of {inr(r.payment)}."
        )
    else:
        parts.append(
            f"Under the second-price rule, {r.winner} pays the second-highest bid of {inr(r.payment)}."
        )
    if r.payoff_sign == "zero":
        parts.append(
            f"With a valuation of {inr(w.valuation)}, {r.winner} earns a payoff of {inr(r.winner_payoff)} (they pay exactly what the slot is worth to them)."
        )
    elif r.payoff_sign == "positive":
        parts.append(
            f"With a valuation of {inr(w.valuation)}, {r.winner} receives a payoff of {inr(r.winner_payoff)}."
        )
    else:
        parts.append(
            f"With a valuation of {inr(w.valuation)}, {r.winner} pays more than the slot is worth and gets a negative payoff of {inr(r.winner_payoff)}."
        )
    if not r.highest_valued_won:
        parts.append(
            f"The advertiser with the highest valuation ({inr(r.highest_valuation)}) did not win, so the allocation is not efficient."
        )
    return " ".join(parts)


def formulas(mechanism: Mechanism) -> dict[str, str]:
    pay = "p_w = b_w" if mechanism is Mechanism.FIRST_PRICE else "p_w = max_{j≠w} b_j"
    return {
        "winner": "w = argmax_i b_i",
        "payment": pay,
        "payoff": "u_i = v_i − p_i if i wins, else 0",
        "revenue": "R = Σ p_i",
    }
