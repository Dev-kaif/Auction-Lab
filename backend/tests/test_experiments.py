import csv
import io
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, initialize_database
from app.experiments import AUTOMATIC, MANUAL, csv_content, details, find_idempotent, list_experiments, overview_stats, save_manual, save_simulation
from app.models import Experiment


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    initialize_database(engine)
    with Session(engine, expire_on_commit=False) as db:
        yield db
    Base.metadata.drop_all(engine)
    engine.dispose()


def manual_data(strategy='A, "special"'):
    request = {"mechanism": "first_price", "valuations": [100, 80, 60, 40], "bids": [90, 72, 45, 28]}
    rows = [{"advertiser": "A", "valuation": "100.00", "bid": "90.00", "rank": 1, "won": True, "payment": "90.00", "payoff": "10.00"},
            {"advertiser": "B", "valuation": "80.00", "bid": "72.00", "rank": 2, "won": False, "payment": "0.00", "payoff": "0.00"},
            {"advertiser": "C", "valuation": "60.00", "bid": "45.00", "rank": 3, "won": False, "payment": "0.00", "payoff": "0.00"},
            {"advertiser": "D", "valuation": "40.00", "bid": "28.00", "rank": 4, "won": False, "payment": "0.00", "payoff": "0.00"}]
    result = {"mechanism": "first_price", "winner": "A", "payment": "90.00", "revenue": "90.00", "winner_payoff": "10.00",
              "advertisers": rows, "strategy_label": strategy}
    return request, result


def automatic_data():
    request = {"n_auctions": 25, "mechanism": "both", "valuation": {"mode": "random", "low": 0.0, "high": 100.0},
               "seed": None, "profiles": [{"label": 'truthful, "base"', "alphas": [1, 1, 1, 1]}]}
    block = {"profile_label": 'truthful, "base"', "alphas": [1, 1, 1, 1], "mechanism": "first_price", "revenue":
             {"mean": 50.25, "median": 50, "std": 2, "se": 1}, "avg_winner_payoff": 5, "avg_bidder_surplus": 1.25,
             "highest_value_win_rate": 1.0, "overbid_rate": 0, "negative_winner_payoff_rate": 0,
             "win_rate": {"A": .4, "B": .3, "C": .2, "D": .1}, "avg_payoff": {"A": 2, "B": 2, "C": 1, "D": 0}}
    result = {"n_auctions": 25, "seed": 123, "seed_was_generated": True, "mechanisms": ["first_price", "second_price"],
              "valuation": {"mode": "random", "low": 0, "high": 100, "distribution": "uniform", "fixed_values": None},
              "results": [block, {**block, "mechanism": "second_price"}]}
    return request, result


def test_database_init_and_manual_save_detail_and_csv(session):
    request, result = manual_data()
    saved = save_manual(session, request, result)
    fetched = session.get(Experiment, saved.id)
    assert fetched is not None and fetched.experiment_type == MANUAL
    assert details(fetched)["configuration"] == {"mechanism": "first_price", "valuations": [100, 80, 60, 40], "bids": [90, 72, 45, 28]}
    content = csv_content(fetched)
    rows = list(csv.DictReader(io.StringIO(content.lstrip("\ufeff"))))
    assert list(rows[0]) == ["experiment_id", "created_at", "mechanism", "advertiser", "valuation", "bid", "rank", "winner", "payment", "payoff"]
    assert len(rows) == 4 and rows[0]["winner"] == "True" and rows[0]["payoff"] == "10.00"


def test_simulation_persists_only_aggregate_results_and_exports_configuration(session):
    request, result = automatic_data()
    saved = save_simulation(session, request, result)
    assert saved.experiment_type == AUTOMATIC and saved.metrics["n_auctions"] == 25
    assert saved.configuration["resolved_seed"] == 123 and saved.configuration["seed_was_generated"] is True
    content = csv_content(saved)
    rows = list(csv.DictReader(io.StringIO(content.lstrip("\ufeff"))))
    assert len(rows) == 2 and rows[0]["valuation_low"] == "0" and rows[0]["seed"] == "123"
    assert rows[0]["strategy"] == 'truthful, "base"' and rows[0]["mean_revenue"] == "50.25"
    assert "auctions" not in saved.result


def test_history_filter_sort_and_overview_counts(session):
    manual_req, manual_res = manual_data()
    first = save_manual(session, manual_req, manual_res)
    first.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    auto_req, auto_res = automatic_data()
    middle = save_simulation(session, auto_req, auto_res)
    middle.created_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    newest = Experiment(experiment_type=MANUAL, mechanism="second_price", strategy="Submitted bids",
                        configuration={}, result=manual_res, metrics={"winner": "B", "revenue": "40.00", "winner_payoff": "5.00"},
                        created_at=datetime(2025, 1, 3, tzinfo=timezone.utc))
    session.add(newest)
    session.commit()
    all_rows, total = list_experiments(session, sort="asc")
    only_manual, manual_count = list_experiments(session, MANUAL, "desc")
    assert total == 3 and manual_count == 2 and all_rows[0].id == first.id
    assert all_rows[-1].id == newest.id and only_manual[0].mechanism == "second_price"
    stats = overview_stats(session)
    assert (stats["total_experiments"], stats["manual_auctions"], stats["automatic_simulations"]) == (3, 2, 1)
    assert len(stats["recent_experiments"]) == 3


def test_delete_experiment_removes_record(session):
    request, result = manual_data()
    saved = save_manual(session, request, result)
    experiment_id = saved.id
    session.delete(saved)
    session.commit()
    assert session.get(Experiment, experiment_id) is None
    assert list_experiments(session)[1] == 0


def test_idempotency_returns_existing_result_and_rejects_key_reuse(session):
    request, result = manual_data()
    saved = save_manual(session, request, result, "request-1")
    assert find_idempotent(session, "request-1", MANUAL, request).id == saved.id
    changed = {**request, "bids": [91, 72, 45, 28]}
    with pytest.raises(HTTPException) as error:
        find_idempotent(session, "request-1", MANUAL, changed)
    assert error.value.status_code == 409


def test_csv_writer_quotes_comma_and_quote_in_strategy(session):
    request, result = automatic_data()
    saved = save_simulation(session, request, result)
    rows = list(csv.reader(io.StringIO(csv_content(saved).lstrip("\ufeff"))))
    strategy_i = rows[0].index("strategy")
    assert rows[1][strategy_i] == 'truthful, "base"'
