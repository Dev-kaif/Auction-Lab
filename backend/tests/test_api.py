import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
V = [100, 80, 60, 40]


def run(mech, bids, vals=V):
    return client.post("/api/auctions/run", json={"mechanism": mech, "valuations": vals, "bids": bids})


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_second_price_example():
    r = run("second_price", V)
    assert r.status_code == 200
    d = r.json()
    assert (d["winner"], d["payment"], d["winner_payoff"], d["revenue"]) == ("A", "80.00", "20.00", "80.00")
    assert d["ranking"] == ["A", "B", "C", "D"]
    assert "pays the second-highest bid of ₹80.00" in d["explanation"]
    assert d["formulas"]["payment"] == "p_w = max_{j≠w} b_j"


def test_first_price_example():
    d = run("first_price", V).json()
    assert (d["payment"], d["winner_payoff"], d["revenue"]) == ("100.00", "0.00", "100.00")
    assert "pays their own bid" in d["explanation"]


def test_strategic_example_and_efficiency_flag():
    d = run("second_price", [75, 80, 60, 40]).json()
    assert d["winner"] == "B" and d["payment"] == "75.00" and d["winner_payoff"] == "5.00"
    assert d["highest_valued_won"] is False and "not efficient" in d["explanation"]
    rows = {x["advertiser"]: x for x in d["advertisers"]}
    assert rows["B"]["outcome"] == "Won" and rows["A"]["outcome"] == "Lost"
    assert rows["B"]["rank"] == 1 and rows["A"]["rank"] == 2


def test_tie_explained():
    d = run("first_price", [50, 70, 70, 10]).json()
    assert d["winner"] == "B" and d["tie_for_highest_bid"] and d["tied_bidders"] == ["B", "C"]
    assert "tie-break" in d["explanation"]


def test_negative_payoff_explained():
    d = run("first_price", [100, 80, 60, 130]).json()
    assert d["winner"] == "D" and d["winner_payoff"] == "-90.00" and "negative payoff" in d["explanation"]


@pytest.mark.parametrize("body", [
    {"mechanism": "first_price", "valuations": V, "bids": [-1, 1, 1, 1]},       # engine: negative
    {"mechanism": "first_price", "valuations": V, "bids": [1e9, 1, 1, 1]},      # engine: too large
    {"mechanism": "first_price", "valuations": V, "bids": [1, 1, 1]},           # wrong length
    {"mechanism": "third_price", "valuations": V, "bids": V},                   # bad mechanism
    {"mechanism": "first_price", "valuations": V, "bids": ["abc", 1, 1, 1]},    # not a number
    {"mechanism": "first_price", "valuations": V, "bids": [True, 1, 1, 1]},     # boolean
    {"mechanism": "first_price", "valuations": V},                              # missing field
    {"mechanism": "first_price", "valuations": V, "bids": V, "extra": 1},       # unknown field
])
def test_invalid_requests_give_readable_422(body):
    r = client.post("/api/auctions/run", json=body)
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] in {"validation_error", "invalid_input"} and err["message"]


def test_non_finite_json_rejected():
    r = client.post("/api/auctions/run", content='{"mechanism":"first_price","valuations":[1,1,1,1],"bids":[NaN,1,1,1]}',
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_cors_allows_dev_origin_only():
    ok = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in bad.headers
