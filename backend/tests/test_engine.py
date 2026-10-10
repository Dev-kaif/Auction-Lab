from decimal import Decimal as D

import numpy as np
import pytest

from app.auctions.engine import run_auction
from app.auctions.models import AuctionInputError, Mechanism
from app.auctions.strategies import FixedFraction, Truthful, bids_from_strategies
from app.simulation.valuations import generate_uniform_valuations

V = [100, 80, 60, 40]
FP, SP = Mechanism.FIRST_PRICE, Mechanism.SECOND_PRICE


# ---- Spec example 1: truthful bids ----
def test_truthful_first_price():
    r = run_auction(V, V, FP)
    assert (r.winner, r.payment, r.winner_payoff, r.revenue) == ("A", D("100"), D("0"), D("100"))


def test_truthful_second_price():
    r = run_auction(V, V, SP)
    assert (r.winner, r.payment, r.winner_payoff, r.revenue) == ("A", D("80"), D("20"), D("80"))


# ---- Spec example 2: strategic bidding ----
@pytest.mark.parametrize("mech,pay,payoff", [(FP, "80", "0"), (SP, "75", "5")])
def test_strategic_bidding(mech, pay, payoff):
    r = run_auction(V, [75, 80, 60, 40], mech)
    assert r.winner == "B" and r.winning_bid == D("80")
    assert r.payment == D(pay) and r.winner_payoff == D(payoff)
    assert not r.highest_valued_won  # A has the top valuation but lost


# ---- Winner determination and ties ----
def test_unique_highest_bid_and_ranks():
    r = run_auction(V, [10, 50, 30, 20], FP)
    assert r.winner == "B"
    assert [x.rank for x in r.results] == [4, 1, 2, 3]
    assert not r.tie_for_highest_bid


def test_tie_goes_to_lowest_index():
    for mech in (FP, SP):
        r = run_auction(V, [50, 70, 70, 10], mech)
        assert r.winner == "B"
        assert r.tie_for_highest_bid and r.tied_bidders == ("B", "C")
        assert [x.rank for x in r.results] == [3, 1, 2, 4]


def test_tie_second_price_pays_tied_bid():
    r = run_auction(V, [70, 70, 10, 10], SP)
    assert r.winner == "A" and r.payment == D("70") and r.winner_payoff == D("30")


def test_all_zero_bids():
    r = run_auction(V, [0, 0, 0, 0], SP)
    assert r.winner == "A" and r.payment == D("0") and r.winner_payoff == D("100")
    r = run_auction(V, [0, 0, 0, 0], FP)
    assert r.revenue == D("0") and r.tie_for_highest_bid


def test_multiple_tied_runner_ups():
    r = run_auction(V, [90, 60, 60, 60], SP)
    assert r.winner == "A" and r.payment == D("60")


def test_zero_valuation_winner_negative_payoff():
    r = run_auction([0, 80, 60, 40], [30, 20, 10, 5], FP)
    assert r.winner == "A" and r.winner_payoff == D("-30") and r.payoff_sign == "negative"


def test_overbid_negative_payoff_and_flag():
    r = run_auction(V, [100, 80, 60, 130], FP)
    assert r.winner == "D" and r.winner_payoff == D("-90") and r.any_overbid
    assert [x.overbid for x in r.results] == [False, False, False, True]


def test_payoff_uses_valuation_not_bid():
    r = run_auction(V, [60, 10, 10, 10], SP)  # A shades heavily; pays 10
    assert r.winner_payoff == D("90")


def test_losers_pay_and_earn_zero_and_revenue_equals_payment():
    r = run_auction(V, V, SP)
    for x in r.results:
        if not x.won:
            assert x.payment == 0 and x.payoff == 0
    assert r.revenue == sum(x.payment for x in r.results) == r.payment


def test_payoff_signs():
    assert run_auction(V, V, FP).payoff_sign == "zero"
    assert run_auction(V, V, SP).payoff_sign == "positive"


def test_second_price_truthful_is_weakly_dominant_grid():
    # For many opponent bid profiles, no deviation beats truthful bidding for A.
    for opp in [(80, 60, 40), (120, 10, 10), (95, 95, 0), (100, 50, 50), (0, 0, 0)]:
        truthful = run_auction(V, [100, *opp], SP).results[0].payoff
        for dev in range(0, 201, 5):
            assert run_auction(V, [dev, *opp], SP).results[0].payoff <= truthful


def test_first_price_shading_can_beat_truthful():
    truthful = run_auction(V, [100, 80, 60, 40], FP).results[0].payoff
    shaded = run_auction(V, [85, 80, 60, 40], FP).results[0].payoff
    assert truthful == 0 and shaded == D("15")


# ---- Validation ----
@pytest.mark.parametrize("bad", [-1, float("nan"), float("inf"), "abc", None, True, 10**9])
def test_invalid_bid_values(bad):
    with pytest.raises(AuctionInputError):
        run_auction(V, [bad, 1, 1, 1], FP)


def test_invalid_valuation_and_length():
    with pytest.raises(AuctionInputError):
        run_auction([-5, 1, 1, 1], V, FP)
    with pytest.raises(AuctionInputError):
        run_auction(V[:3], V, FP)
    with pytest.raises(AuctionInputError):
        run_auction(V, V + [1], FP)
    with pytest.raises(AuctionInputError):
        run_auction(5, V, FP)


def test_invalid_mechanism():
    with pytest.raises(ValueError):
        run_auction(V, V, "third_price")


def test_money_has_no_float_artifacts():
    r = run_auction([0.1, 0.2, 0.3, 0.4], [0.1, 0.2, 0.3, 0.4], SP)
    assert r.payment == D("0.30") and r.winner_payoff == D("0.10")


# ---- Strategies ----
def test_strategies_bids():
    assert Truthful().bid(100) == D("100.00")
    assert FixedFraction("0.8").bid(100) == D("80.00")
    assert FixedFraction(0.75).bid(80) == D("60.00")
    assert FixedFraction("1.5").bid(100) == D("150.00")
    assert FixedFraction(0).bid(100) == D("0.00")


@pytest.mark.parametrize("bad", [-0.1, 1.51, float("nan"), float("inf"), "x", True])
def test_invalid_alpha(bad):
    with pytest.raises(AuctionInputError):
        FixedFraction(bad)


def test_bids_from_strategies_deviator():
    bids = bids_from_strategies(V, [FixedFraction("0.75"), Truthful(), Truthful(), Truthful()])
    assert bids == [D("75.00"), D("80.00"), D("60.00"), D("40.00")]
    assert run_auction(V, bids, SP).winner == "B"


# ---- Reproducibility and scenario consistency ----
def test_seed_reproducible():
    a = generate_uniform_valuations(500, 0, 100, seed=42)
    b = generate_uniform_valuations(500, 0, 100, seed=42)
    c = generate_uniform_valuations(500, 0, 100, seed=43)
    assert a.shape == (500, 4) and np.array_equal(a, b) and not np.array_equal(a, c)
    assert a.min() >= 0 and a.max() <= 100


def test_same_scenarios_reused_across_mechanisms():
    vals = generate_uniform_valuations(50, 0, 100, seed=7)
    for row in vals:
        v = [round(float(x), 2) for x in row]
        fp, sp = run_auction(v, v, FP), run_auction(v, v, SP)
        assert fp.winner == sp.winner  # same bids -> same winner
        assert sp.revenue <= fp.revenue  # truthful: 2nd price never exceeds 1st


@pytest.mark.parametrize("args", [(0, 0, 100), (10, 100, 100), (10, 50, 10), (10, -1, 10),
                                  (10, 0, float("inf")), (10, 0, float("nan")), (True, 0, 100)])
def test_invalid_valuation_generation(args):
    with pytest.raises(AuctionInputError):
        generate_uniform_valuations(*args, seed=1)


# ---- Statistical sanity check against theory (n=4, U[0,100]) ----
def _revenue_at_alpha(alpha, mech, vals):
    s = FixedFraction(alpha)
    total = D(0)
    for row in vals:
        v = [round(float(x), 2) for x in row]
        total += run_auction(v, [s.bid(x) for x in v], mech).revenue
    return float(total) / len(vals)


def test_equilibrium_revenue_equivalence():
    """Truthful 2nd-price and alpha=0.75 1st-price both have E[revenue] = 60."""
    vals = generate_uniform_valuations(4000, 0, 100, seed=2024)
    sp = _revenue_at_alpha(1.0, SP, vals)
    fp = _revenue_at_alpha(0.75, FP, vals)
    assert abs(sp - 60) < 1.5 and abs(fp - 60) < 1.5
    assert abs(sp - fp) < 1.5
