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
    elif result.mechanism is Mechanism.SECOND_PRICE:
        parts.append(
            f"Under the second-price rule, {result.winner} pays the second-highest "
            f"bid of {inr(result.payment)}."
        )
    elif result.mechanism is Mechanism.GSP:
        parts.append(
            f"In GSP, assigned advertisers pay the next-ranked bid per click, "
            f"scaled by their slot click-through rate; expected platform revenue "
            f"is {inr(result.revenue)} per impression."
        )
    else:
        parts.append(
            f"In VCG, each assigned advertiser pays the expected welfare "
            f"externality imposed on the other advertisers; total revenue is "
            f"{inr(result.revenue)} per impression."
        )
    if result.is_multi_slot:
        for row in result.results:
            if row.slot is None:
                continue
            expected_value = row.valuation * Decimal(str(row.click_through_rate))
            parts.append(
                f"{row.advertiser} receives Slot {row.slot} (CTR {row.click_through_rate:.2f}): "
                f"expected value {inr(expected_value)}, expected payment {inr(row.expected_payment)}, "
                f"and expected utility {inr(row.expected_utility)} per impression."
            )
        parts.append(f"Social welfare is {inr(result.social_welfare)} per impression.")
        return " ".join(parts)
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
    payment_formula = {
        Mechanism.FIRST_PRICE: "p_w = b_w",
        Mechanism.SECOND_PRICE: "p_w = max_{j≠w} b_j",
        Mechanism.GSP: "p_i(click) = b_{next(i)}; E[p_i] = CTR_{slot(i)} × p_i(click)",
        Mechanism.VCG: "E[p_i] = W_{-i}^{without i} − W_{-i}^{with i}",
    }[mechanism]
    winner_formula = (
        "assign slots in descending bid order; ties follow A → B → C → D"
        if mechanism in (Mechanism.GSP, Mechanism.VCG)
        else "w = argmax_i b_i"
    )
    return {
        "winner": winner_formula,
        "payment": payment_formula,
        "payoff": "u_i = v_i − p_i if i wins, else 0",
        "revenue": "R = Σ p_i",
        "expected_value": "E[value_i] = CTR_{slot(i)} × v_i",
        "expected_utility": "E[u_i] = CTR_{slot(i)} × v_i − E[p_i]",
        "social_welfare": "W = Σ_i CTR_{slot(i)} × v_i",
    }
