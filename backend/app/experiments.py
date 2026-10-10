from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import Experiment

MANUAL = "manual_auction"
AUTOMATIC = "automatic_simulation"


def find_idempotent(session: Session, key: str | None, experiment_type: str, request: dict) -> Experiment | None:
    if not key:
        return None
    saved = session.scalar(select(Experiment).where(Experiment.idempotency_key == key))
    if saved is None:
        return None
    saved_request = dict(saved.configuration)
    if experiment_type == AUTOMATIC:
        saved_request.pop("resolved_seed", None)
        saved_request.pop("seed_was_generated", None)
    if saved.experiment_type != experiment_type or saved_request != request:
        raise HTTPException(status_code=409, detail="Idempotency-Key was already used for a different experiment request.")
    return saved


def save_manual(session: Session, request: dict, result: dict, idempotency_key: str | None = None) -> Experiment:
    experiment = Experiment(
        experiment_type=MANUAL, idempotency_key=idempotency_key, mechanism=request["mechanism"], strategy="Submitted bids",
        configuration={"mechanism": request["mechanism"], "valuations": request["valuations"], "bids": request["bids"]},
        result=result,
        metrics={"winner": result["winner"], "payment": result["payment"], "revenue": result["revenue"],
                 "winner_payoff": result["winner_payoff"]},
    )
    session.add(experiment)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        previous = find_idempotent(session, idempotency_key, MANUAL, request)
        if previous is not None:
            return previous
        raise
    session.refresh(experiment)
    return experiment


def save_simulation(session: Session, request: dict, result: dict, idempotency_key: str | None = None) -> Experiment:
    labels = [p["label"] for p in request["profiles"]]
    mechanisms = result["mechanisms"]
    means = [block["revenue"]["mean"] for block in result["results"]]
    experiment = Experiment(
        experiment_type=AUTOMATIC, idempotency_key=idempotency_key, mechanism="both" if len(mechanisms) == 2 else mechanisms[0],
        strategy="; ".join(labels),
        configuration={**request, "resolved_seed": result["seed"], "seed_was_generated": result["seed_was_generated"]},
        result=result,
        metrics={"n_auctions": result["n_auctions"], "seed": result["seed"], "mean_revenue": means,
                 "profile_count": len(labels), "result_count": len(result["results"])},
    )
    session.add(experiment)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        previous = find_idempotent(session, idempotency_key, AUTOMATIC, request)
        if previous is not None:
            return previous
        raise
    session.refresh(experiment)
    return experiment


def summary(experiment: Experiment) -> dict[str, Any]:
    return {"id": experiment.id, "created_at": _iso(experiment.created_at), "experiment_type": experiment.experiment_type,
            "mechanism": experiment.mechanism, "strategy": experiment.strategy, "metrics": experiment.metrics}


def details(experiment: Experiment) -> dict[str, Any]:
    return {**summary(experiment), "configuration": experiment.configuration, "result": experiment.result}


def list_experiments(session: Session, experiment_type: str | None = None, sort: str = "desc") -> tuple[list[Experiment], int]:
    query: Select[tuple[Experiment]] = select(Experiment)
    count_query = select(func.count()).select_from(Experiment)
    if experiment_type:
        query = query.where(Experiment.experiment_type == experiment_type)
        count_query = count_query.where(Experiment.experiment_type == experiment_type)
    order = Experiment.created_at.asc() if sort == "asc" else Experiment.created_at.desc()
    rows = list(session.scalars(query.order_by(order, Experiment.id)).all())
    total = int(session.scalar(count_query) or 0)
    return rows, total


def overview_stats(session: Session) -> dict[str, Any]:
    total = int(session.scalar(select(func.count()).select_from(Experiment)) or 0)
    manual = int(session.scalar(select(func.count()).select_from(Experiment).where(Experiment.experiment_type == MANUAL)) or 0)
    automatic = int(session.scalar(select(func.count()).select_from(Experiment).where(Experiment.experiment_type == AUTOMATIC)) or 0)
    recent = session.scalars(select(Experiment).order_by(Experiment.created_at.desc(), Experiment.id).limit(5)).all()
    return {"total_experiments": total, "manual_auctions": manual, "automatic_simulations": automatic,
            "recent_experiments": [summary(item) for item in recent]}


def csv_content(experiment: Experiment) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    if experiment.experiment_type == MANUAL:
        writer.writerow(["experiment_id", "created_at", "mechanism", "advertiser", "valuation", "bid", "rank", "winner", "payment", "payoff"])
        for advertiser in experiment.result["advertisers"]:
            writer.writerow([experiment.id, _iso(experiment.created_at), experiment.mechanism, advertiser["advertiser"],
                             advertiser["valuation"], advertiser["bid"], advertiser["rank"], advertiser["won"],
                             advertiser["payment"], advertiser["payoff"]])
    else:
        writer.writerow(["experiment_id", "created_at", "n_auctions", "seed", "seed_was_generated", "valuation_mode",
                         "valuation_low", "valuation_high", "fixed_values", "mechanism", "strategy", "alphas",
                         "mean_revenue", "revenue_median", "revenue_std", "revenue_se", "revenue_min", "revenue_max",
                         "avg_winning_bid", "avg_winning_payment", "mean_winner_payoff", "mean_bidder_surplus",
                         "highest_value_win_rate", "overbid_rate", "negative_winner_payoff_rate",
                         "win_rate_A", "win_rate_B", "win_rate_C", "win_rate_D", "mean_payoff_A", "mean_payoff_B",
                         "mean_payoff_C", "mean_payoff_D"])
        for block in experiment.result["results"]:
            revenue = block["revenue"]
            valuation = experiment.result["valuation"]
            writer.writerow([experiment.id, _iso(experiment.created_at), experiment.result["n_auctions"], experiment.result["seed"],
                             experiment.result["seed_was_generated"], valuation.get("mode"), valuation.get("low"), valuation.get("high"),
                             _json_cell(valuation.get("fixed_values")), block["mechanism"], _safe_text(block["profile_label"]), _json_cell(block["alphas"]), revenue["mean"], revenue["median"],
                             revenue["std"], revenue["se"], revenue.get("min"), revenue.get("max"), block.get("avg_winning_bid"),
                             block.get("avg_winning_payment"), block["avg_winner_payoff"], block["avg_bidder_surplus"],
                             block["highest_value_win_rate"], block["overbid_rate"], block["negative_winner_payoff_rate"],
                             *(block["win_rate"][a] for a in "ABCD"), *(block["avg_payoff"][a] for a in "ABCD")])
    return "\ufeff" + buffer.getvalue()


def _json_cell(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _safe_text(value: str) -> str:
    return f"'{value}" if value.startswith(("=", "+", "-", "@", "\t", "\r")) else value


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
