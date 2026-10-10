import csv
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import get_session, initialize_database
from app.main import app


@pytest.fixture
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'api-tests.db'}", connect_args={"check_same_thread": False})
    initialize_database(engine)
    Factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def test_session():
        with Factory() as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)
        engine.dispose()


def test_manual_save_idempotency_and_failed_requests_are_not_saved(client):
    request = {"mechanism": "first_price", "valuations": [100, 80, 60, 40], "bids": [90, 72, 45, 28]}
    first = client.post("/api/auctions/run", json=request, headers={"Idempotency-Key": "manual-action-1"})
    repeat = client.post("/api/auctions/run", json=request, headers={"Idempotency-Key": "manual-action-1"})
    assert first.status_code == 200 and repeat.json() == first.json()
    history = client.get("/api/experiments?experiment_type=manual_auction&sort=desc").json()
    assert history["total"] == 1 and history["items"][0]["metrics"]["winner"] == "A"
    conflict = client.post("/api/auctions/run", json={**request, "bids": [91, 72, 45, 28]},
                           headers={"Idempotency-Key": "manual-action-1"})
    assert conflict.status_code == 409
    invalid = client.post("/api/auctions/run", json={**request, "bids": [1, 2]})
    assert invalid.status_code == 422
    assert client.get("/api/experiments").json()["total"] == 1


def test_simulation_history_details_sweep_csv_overview_and_delete(client):
    request = {"n_auctions": 40, "mechanism": "both", "seed": 55,
               "valuation": {"mode": "random", "low": 0, "high": 100},
               "profiles": [{"label": 'baseline, "truthful"', "alphas": [1, 1, 1, 1]}]}
    run = client.post("/api/simulations/run", json=request, headers={"Idempotency-Key": "simulation-action-1"})
    assert run.status_code == 200 and run.json()["seed"] == 55
    experiment_id = client.get("/api/experiments?experiment_type=automatic_simulation").json()["items"][0]["id"]
    detail = client.get(f"/api/experiments/{experiment_id}").json()
    assert detail["configuration"]["resolved_seed"] == 55 and len(detail["result"]["results"]) == 2
    exported = client.get(f"/api/experiments/{experiment_id}/csv")
    rows = list(csv.DictReader(io.StringIO(exported.text.lstrip("\ufeff"))))
    assert exported.headers["content-type"].startswith("text/csv")
    assert len(rows) == 2 and rows[0]["strategy"] == 'baseline, "truthful"' and rows[0]["seed"] == "55"
    before_sweep = client.get("/api/experiments").json()["total"]
    sweep = client.post("/api/simulations/sweep", json={"n_auctions": 20, "seed": 55, "mechanism": "first_price", "alphas": [0.5, 1.0]})
    assert sweep.status_code == 200 and client.get("/api/experiments").json()["total"] == before_sweep
    stats = client.get("/api/overview").json()
    assert stats["total_experiments"] == 1 and stats["automatic_simulations"] == 1
    deleted = client.delete(f"/api/experiments/{experiment_id}")
    assert deleted.status_code == 200 and deleted.json()["deleted"] is True
    assert client.get(f"/api/experiments/{experiment_id}").status_code == 404


def test_multislot_api_manual_simulation_sweep_and_history(client):
    manual = client.post("/api/auctions/run", json={
        "mechanism": "gsp", "valuations": [100, 80, 60, 40],
        "bids": [100, 80, 60, 40], "click_through_rates": [1, .7, .4],
    })
    assert manual.status_code == 200
    manual_result = manual.json()
    assert manual_result["is_multi_slot"] is True
    assert [row["slot"] for row in manual_result["advertisers"]] == [1, 2, 3, None]
    assert [row["expected_payment"] for row in manual_result["advertisers"]] == ["80.00", "42.00", "16.00", "0.00"]
    assert manual_result["revenue"] == "138.00" and manual_result["social_welfare"] == "180.00"
    assert "expected_utility" in manual_result["formulas"]

    invalid_rates = client.post("/api/auctions/run", json={
        "mechanism": "vcg", "valuations": [100, 80, 60, 40], "bids": [100, 80, 60, 40],
        "click_through_rates": [1, .8, .9],
    })
    assert invalid_rates.status_code == 422

    simulation = client.post("/api/simulations/run", json={
        "n_auctions": 10, "mechanism": "all", "click_through_rates": [1, .7, .4],
        "seed": 17, "valuation": {"mode": "fixed", "fixed_values": [100, 80, 60, 40]},
        "profiles": [{"label": "truthful", "alphas": [1, 1, 1, 1]}],
    })
    assert simulation.status_code == 200
    body = simulation.json()
    assert body["mechanisms"] == ["first_price", "second_price", "gsp", "vcg"]
    gsp = next(result for result in body["results"] if result["mechanism"] == "gsp")
    vcg = next(result for result in body["results"] if result["mechanism"] == "vcg")
    assert gsp["revenue"]["mean"] == pytest.approx(138)
    assert gsp["avg_social_welfare"] == pytest.approx(180)
    assert vcg["avg_expected_payment"] == pytest.approx(108)
    assert sum(gsp["win_rate"].values()) == pytest.approx(3)

    sweep = client.post("/api/simulations/sweep", json={
        "n_auctions": 20, "seed": 17, "mechanism": "gsp", "alphas": [.8, 1.0],
        "click_through_rates": [1, .7, .4],
    })
    assert sweep.status_code == 200
    assert len(sweep.json()["points"]["gsp"]) == 2
    assert sweep.json()["click_through_rates"] == [1, .7, .4]

    history = client.get("/api/experiments?experiment_type=manual_auction").json()
    record = client.get(f"/api/experiments/{history['items'][0]['id']}").json()
    assert record["configuration"]["click_through_rates"] == [1, .7, .4]
    exported = client.get(f"/api/experiments/{history['items'][0]['id']}/csv").text
    assert "payment_per_click" in exported and "expected_utility_per_impression" in exported
