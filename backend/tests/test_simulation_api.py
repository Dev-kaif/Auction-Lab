import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
T = {"label": "truthful", "alphas": [1, 1, 1, 1]}


def post(body, path="/api/simulations/run"):
    return client.post(path, json=body)


def test_run_both_mechanisms_shape_and_values():
    r = post({"n_auctions": 200, "mechanism": "both", "seed": 7, "profiles": [T, {"label": "eighty", "alphas": [.8, .8, .8, .8]}]})
    assert r.status_code == 200
    d = r.json()
    assert d["n_auctions"] == 200 and d["seed"] == 7 and d["seed_was_generated"] is False
    assert len(d["results"]) == 4 and d["mechanisms"] == ["first_price", "second_price"]
    assert "win_rate" in d["definitions"] and d["valuation"]["distribution"] == "uniform"
    for b in d["results"]:
        assert sum(b["win_rate"].values()) == pytest.approx(1.0)
        assert sum(b["revenue_histogram"]["counts"]) == 200


def test_seed_generated_when_omitted_and_rerun_reproduces():
    a = post({"n_auctions": 100, "profiles": [T]}).json()
    assert a["seed_was_generated"] is True
    b = post({"n_auctions": 100, "seed": a["seed"], "profiles": [T]}).json()
    assert a["results"] == b["results"]


def test_fixed_mode_example_and_note():
    d = post({"n_auctions": 100, "mechanism": "second_price", "valuation": {"mode": "fixed", "fixed_values": [100, 80, 60, 40]},
              "profiles": [T]}).json()
    b = d["results"][0]
    assert b["revenue"]["mean"] == 80 and b["avg_winner_payoff"] == 20 and b["win_rate"]["A"] == 1.0
    assert d["notes"] and d["valuation"]["low"] is None


def test_revenue_equivalence_through_api():
    d = post({"n_auctions": 10000, "seed": 11, "profiles": [{"label": "eq", "alphas": [.75] * 4}, T]}).json()
    fp = next(r for r in d["results"] if r["profile_label"] == "eq" and r["mechanism"] == "first_price")
    sp = next(r for r in d["results"] if r["profile_label"] == "truthful" and r["mechanism"] == "second_price")
    assert abs(fp["revenue"]["mean"] - 60) < 1.0 and abs(sp["revenue"]["mean"] - 60) < 1.0


@pytest.mark.parametrize("body", [
    {"n_auctions": 0, "profiles": [T]},
    {"n_auctions": 10001, "profiles": [T]},
    {"n_auctions": "100", "profiles": [T]},
    {"n_auctions": 100},                                                     # no profiles
    {"n_auctions": 100, "profiles": []},
    {"n_auctions": 100, "profiles": [T, T]},                                 # duplicate labels
    {"n_auctions": 100, "profiles": [{"label": "x", "alphas": [1, 1, 1, 1.6]}]},
    {"n_auctions": 100, "profiles": [{"label": "x", "alphas": [1, 1, 1]}]},
    {"n_auctions": 100, "profiles": [{"label": "", "alphas": [1] * 4}]},
    {"n_auctions": 100, "mechanism": "third_price", "profiles": [T]},
    {"n_auctions": 100, "valuation": {"mode": "random", "low": 80, "high": 20}, "profiles": [T]},
    {"n_auctions": 100, "valuation": {"mode": "fixed"}, "profiles": [T]},
    {"n_auctions": 100, "seed": -3, "profiles": [T]},
    {"n_auctions": 100, "profiles": [T], "surprise": 1},
])
def test_invalid_run_requests_422(body):
    r = post(body)
    assert r.status_code == 422
    e = r.json()["error"]
    assert e["code"] in {"validation_error", "invalid_input"} and e["message"]


def test_sweep_endpoint():
    d = post({"n_auctions": 2000, "seed": 4, "mode": "deviator", "deviator": "C", "alphas": [0.5, 0.75, 1.0]}, "/api/simulations/sweep").json()
    assert set(d["points"]) == {"first_price", "second_price"} and d["deviator"] == "C"
    assert [p["alpha"] for p in d["points"]["first_price"]] == [0.5, 0.75, 1.0]
    assert d["points"]["first_price"][0]["deviator_win_rate"] is not None


def test_sweep_default_grid_and_validation():
    d = post({"n_auctions": 500, "seed": 1, "mechanism": "first_price"}, "/api/simulations/sweep").json()
    pts = d["points"]["first_price"]
    assert pts[0]["alpha"] == 0.1 and pts[-1]["alpha"] == 1.5 and len(pts) == 29
    assert pts[0]["deviator_mean_payoff"] is None
    assert post({"alphas": [2.0]}, "/api/simulations/sweep").status_code == 422
    assert post({"n_auctions": 20000}, "/api/simulations/sweep").status_code == 422


def test_openapi_lists_simulation_routes():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/simulations/run" in paths and "/api/simulations/sweep" in paths
