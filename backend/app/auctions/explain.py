"""Generate the explanation text from an actual AuctionResult (never hardcoded)."""

from __future__ import annotations

from decimal import Decimal

from .models import AuctionResult, Mechanism


def inr(amount: Decimal) -> str:
    """Format one exact amount with Indian currency symbol and two decimals."""
    sign = "-" if amount < 0 else ""
    return f"{sign}₹{abs(amount):,.2f}"


def explain(result: AuctionResult) -> str:
    """Build a short explanation using the auction engine's computed result."""
    winner_row = next(row for row in result.results if row.won)
    parts = [
        f"Advertiser {result.winner} submitted the highest bid of "
        f"{inr(result.winning_bid)} and won."
    ]
    if result.tie_for_highest_bid:
        parts.append(
            f"Advertisers {', '.join(result.tied_bidders)} tied for the highest bid; "
            f"the tie-break rule (lowest index first) awarded the slot to {result.winner}."
        )
    if result.mechanism is Mechanism.FIRST_PRICE:
        parts.append(
            f"Under the first-price rule, {result.winner} pays their own bid of "
            f"{inr(result.payment)}."
        )
    else:
        parts.append(
            f"Under the second-price rule, {result.winner} pays the second-highest "
            f"bid of {inr(result.payment)}."
        )
    if result.payoff_sign == "zero":
        parts.append(
            f"With a valuation of {inr(winner_row.valuation)}, {result.winner} earns "
            f"a payoff of {inr(result.winner_payoff)} (they pay exactly what the "
            "slot is worth to them)."
        )
    elif result.payoff_sign == "positive":
        parts.append(
            f"With a valuation of {inr(winner_row.valuation)}, {result.winner} "
            f"receives a payoff of {inr(result.winner_payoff)}."
        )
    else:
        parts.append(
            f"With a valuation of {inr(winner_row.valuation)}, {result.winner} "
            f"pays more than the slot is worth and gets a negative payoff of "
            f"{inr(result.winner_payoff)}."
        )
    if not result.highest_valued_won:
        parts.append(
            f"The advertiser with the highest valuation "
            f"({inr(result.highest_valuation)}) did not win, so the allocation "
            "is not efficient."
        )
    return " ".join(parts)


def formulas(mechanism: Mechanism) -> dict[str, str]:
    # Keep the displayed payment equation in sync with the chosen mechanism.
    payment_formula = (
        "p_w = b_w"
        if mechanism is Mechanism.FIRST_PRICE
        else "p_w = max_{j≠w} b_j"
    )
    return {
        "winner": "w = argmax_i b_i",
        "payment": payment_formula,
        "payoff": "u_i = v_i − p_i if i wins, else 0",
        "revenue": "R = Σ p_i",
    }
