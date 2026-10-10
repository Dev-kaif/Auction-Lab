import json
from decimal import Decimal as D

import numpy as np
import pytest

from app.auctions.engine import run_auction
from app.auctions.models import AuctionInputError, Mechanism
from app.simulation.engine import bids_from_alphas, parse_alphas, run_batch
from app.simulation.runner import run_experiment, run_sweep

FP, SP = Mechanism.FIRST_PRICE, Mechanism.SECOND_PRICE
TRUTH = {"label": "truthful", "alphas": [1, 1, 1, 1]}


def exp(**kw):
    base = dict(n_auctions=1000, mechanism="both", mode="random", low=0, high=100, fixed_values=None,
                seed=1, profiles=[TRUTH])
    base.update(kw)
    return run_experiment(**base)


def block(res, label, mech):
    return next(r for r in res["results"] if r["profile_label"] == label and r["mechanism"] == mech)


# ---- Vectorized engine == exact Decimal engine ----
@pytest.mark.parametrize("mech", [FP, SP])
def test_vectorized_matches_decimal_engine_random(mech):
    rng = np.random.default_rng(0)
    vals = np.round(rng.uniform(0, 100, (400, 4)), 2)
    bids = np.round(rng.uniform(0, 130, (400, 4)), 2)
    b = run_batch(vals, bids, mech)
    for i in range(400):
        r = run_auction([float(x) for x in vals[i]], [float(x) for x in bids[i]], mech)
        assert r.winner_index == b.winner[i]
        assert float(r.payment) == pytest.approx(b.payment[i], abs=1e-9)
        assert float(r.revenue) == pytest.approx(b.revenue[i], abs=1e-9)
        assert [float(x.payoff) for x in r.results] == pytest.approx(list(b.payoffs[i]), abs=1e-9)


@pytest.mark.parametrize("mech", [FP, SP])
def test_vectorized_matches_decimal_engine_with_heavy_ties(mech):
    rng = np.random.default_rng(1)
    vals = rng.integers(0, 6, (400, 4)).astype(float) * 10   # few distinct values -> many ties, zeros
    bids = rng.integers(0, 4, (400, 4)).astype(float) * 10
    b = run_batch(vals, bids, mech)
    for i in range(400):
        r = run_auction([float(x) for x in vals[i]], [float(x) for x in bids[i]], mech)
        assert r.winner_index == b.winner[i]                      # lowest-index tie-break agrees
        assert float(r.payment) == pytest.approx(b.payment[i])
        assert [float(x.payoff) for x in r.results] == pytest.approx(list(b.payoffs[i]))


def test_batch_spec_examples():
    v = np.array([[100, 80, 60, 40.0]])
    assert run_batch(v, v, FP).payment[0] == 100 and run_batch(v, v, SP).payment[0] == 80
    s = np.array([[75, 80, 60, 40.0]])
    assert run_batch(v, s, FP).payoffs[0, 1] == 0 and run_batch(v, s, SP).payoffs[0, 1] == 5


def test_batch_shape_validation():
    with pytest.raises(AuctionInputError):
        run_batch(np.zeros((3, 4)), np.zeros((3, 3)), FP)


def test_alpha_parsing():
    assert list(parse_alphas([0, 0.5, 1, 1.5])) == [0, 0.5, 1, 1.5]
    for bad in ([1, 1, 1], [1, 1, 1, 1.51], [1, 1, 1, -0.1], [1, 1, 1, float("nan")], [1, 1, 1, "x"]):
        with pytest.raises(AuctionInputError):
            parse_alphas(bad)


# ---- Reproducibility, seed, pairing ----
def test_same_seed_identical_results_different_seed_differs():
    a, b, c = exp(seed=5), exp(seed=5), exp(seed=6)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert a["results"][0]["revenue"]["mean"] != c["results"][0]["revenue"]["mean"]


def test_generated_seed_is_returned_and_reproduces():
    a = exp(seed=None)
    assert a["seed_was_generated"] is True
    b = exp(seed=a["seed"])
    assert b["seed_was_generated"] is False
    assert a["results"] == b["results"]


def test_paired_scenarios_across_mechanisms_and_strategies():
    res = exp(profiles=[TRUTH, {"label": "shade", "alphas": [.8] * 4}])
    ft, st = block(res, "truthful", "first_price"), block(res, "truthful", "second_price")
    assert ft["win_rate"] == st["win_rate"]                      # same bids on same scenarios -> same winners
    assert st["revenue"]["mean"] <= ft["revenue"]["mean"] + 1e-9  # pointwise 2nd <= 1st for identical bids
    assert ft["avg_winning_bid"] == st["avg_winning_bid"]
    # truthful first-price revenue = E[max valuation]; uniform scale: shading by .8 scales every bid by .8
    sh = block(res, "shade", "first_price")
    assert sh["revenue"]["mean"] == pytest.approx(0.8 * ft["revenue"]["mean"], rel=1e-3)


# ---- Aggregation correctness ----
def test_fixed_valuations_aggregates_exact():
    res = exp(n_auctions=100, mode="fixed", fixed_values=[100, 80, 60, 40])
    sp, fp = block(res, "truthful", "second_price"), block(res, "truthful", "first_price")
    assert sp["revenue"]["mean"] == 80 and sp["revenue"]["std"] == 0 and sp["revenue"]["se"] == 0
    assert sp["avg_winner_payoff"] == 20 and sp["avg_bidder_surplus"] == 5       # 20 / 4
    assert sp["win_rate"] == {"A": 1.0, "B": 0.0, "C": 0.0, "D": 0.0}
    assert sp["avg_payoff"] == {"A": 20.0, "B": 0.0, "C": 0.0, "D": 0.0}
    assert sp["highest_value_win_rate"] == 1.0 and sp["overbid_rate"] == 0.0
    assert fp["revenue"]["mean"] == 100 and fp["avg_winner_payoff"] == 0
    assert any("deterministic" in n for n in res["notes"])


def test_strategic_fixed_profile():
    res = exp(n_auctions=50, mode="fixed", fixed_values=[100, 80, 60, 40],
              profiles=[{"label": "A shades .75", "alphas": [.75, 1, 1, 1]}])
    sp = block(res, "A shades .75", "second_price")
    assert sp["win_rate"]["B"] == 1.0 and sp["revenue"]["mean"] == 75 and sp["avg_payoff"]["B"] == 5
    assert sp["highest_value_win_rate"] == 0.0


def test_overbid_and_negative_payoff_rates():
    res = exp(n_auctions=40, mode="fixed", fixed_values=[100, 80, 60, 40],
              profiles=[{"label": "over", "alphas": [1.5, 1.5, 1.5, 1.5]}])
    fp = block(res, "over", "first_price")
    assert fp["overbid_rate"] == 1.0 and fp["negative_winner_payoff_rate"] == 1.0
    assert fp["avg_winner_payoff"] == -50                        # A bids 150 on value 100


def test_denominators_sum_properly():
    res = exp(n_auctions=777, profiles=[{"label": "mix", "alphas": [.9, 1, 1.1, .7]}])
    for r in res["results"]:
        assert sum(r["win_rate"].values()) == pytest.approx(1.0)
        assert sum(r["avg_payoff"].values()) == pytest.approx(r["avg_winner_payoff"])
        assert r["avg_bidder_surplus"] == pytest.approx(r["avg_winner_payoff"] / 4)
        assert r["avg_winning_payment"] == pytest.approx(r["revenue"]["mean"])
        assert sum(r["revenue_histogram"]["counts"]) == 777
        assert r["revenue"]["se"] == pytest.approx(r["revenue"]["std"] / np.sqrt(777))
        assert r["revenue"]["min"] <= r["revenue"]["median"] <= r["revenue"]["max"]


def test_shared_histogram_edges_and_convergence_endpoint():
    res = exp(n_auctions=500, profiles=[TRUTH, {"label": "s", "alphas": [.5] * 4}])
    edges = [tuple(r["revenue_histogram"]["edges"]) for r in res["results"]]
    assert len(set(edges)) == 1
    for r in res["results"]:
        c = r["convergence"]
        assert c["n"][0] == 1 and c["n"][-1] == 500
        assert c["mean"][-1] == pytest.approx(r["revenue"]["mean"])   # last checkpoint = overall mean


# ---- Input validation ----
@pytest.mark.parametrize("kw", [
    dict(n_auctions=0), dict(n_auctions=10_001), dict(n_auctions=True), dict(n_auctions=1.5),
    dict(seed=-1), dict(seed=2**31), dict(low=50, high=50), dict(low=-1), dict(high=float("inf")),
    dict(profiles=[]), dict(profiles=[TRUTH, TRUTH]), dict(profiles=[{"label": "x", "alphas": [1, 1, 1, 2]}]),
    dict(profiles=[{"label": f"p{i}", "alphas": [1] * 4} for i in range(9)]),
    dict(mode="fixed"), dict(mode="fixed", fixed_values=[1, 2, 3]), dict(mode="fixed", fixed_values=[-1, 2, 3, 4]),
    dict(mode="weird"), dict(mechanism="third_price"),
])
def test_invalid_experiment_inputs(kw):
    with pytest.raises((AuctionInputError, ValueError)):
        exp(**kw)


# ---- Theory checks (statistical, seeded) ----
def test_revenue_equivalence_at_equilibrium():
    res = exp(n_auctions=10_000, seed=11, profiles=[{"label": "eq", "alphas": [.75] * 4}, TRUTH])
    fp_eq = block(res, "eq", "first_price")["revenue"]
    sp_truth = block(res, "truthful", "second_price")["revenue"]
    assert abs(fp_eq["mean"] - 60) < 4 * fp_eq["se"] + 0.3
    assert abs(sp_truth["mean"] - 60) < 4 * sp_truth["se"] + 0.3


def test_second_price_truthful_dominates_pointwise_in_sweep():
    # Others truthful: on every sample path truthful payoff >= any deviation, so the sums obey it exactly.
    for dev in "ABCD":
        sw = run_sweep(n_auctions=5000, mechanism="second_price", low=0, high=100, seed=3,
                       mode="deviator", deviator=dev, others_alpha=1.0)
        pts = sw["points"]["second_price"]
        truthful = next(p for p in pts if p["alpha"] == 1.0)["deviator_mean_payoff"]
        assert all(p["deviator_mean_payoff"] <= truthful + 1e-9 for p in pts)


def test_first_price_deviator_best_response_near_three_quarters():
    grid = [round(0.5 + 0.05 * k, 2) for k in range(11)]       # 0.50 .. 1.00
    sw = run_sweep(n_auctions=200_000, mechanism="first_price", low=0, high=100, seed=9, mode="deviator",
                   deviator="A", others_alpha=0.75, alphas=grid, max_n=200_000)
    pts = sw["points"]["first_price"]
    best = max(pts, key=lambda p: p["deviator_mean_payoff"])
    assert 0.70 <= best["alpha"] <= 0.80
    truthful = next(p for p in pts if p["alpha"] == 1.0)
    assert truthful["deviator_mean_payoff"] == 0.0               # truthful first-price bidding earns nothing
    assert best["deviator_mean_payoff"] == pytest.approx(5.0, abs=0.5)   # theory: ~5.0 per auction


def test_sweep_validation():
    for kw in (dict(mode="x"), dict(deviator="Z"), dict(alphas=[]), dict(alphas=[2.0]), dict(others_alpha=3), dict(n_auctions=0)):
        with pytest.raises((AuctionInputError, ValueError)):
            run_sweep(**{**dict(n_auctions=100, mechanism="both", low=0, high=100, seed=1), **kw})
