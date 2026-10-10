"""Persistence, history queries, idempotency, and CSV exports for experiments."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Experiment

MANUAL = "manual_auction"
AUTOMATIC = "automatic_simulation"


def find_idempotent(
    session: Session,
    key: str | None,
    experiment_type: str,
    request: dict[str, Any],
) -> Experiment | None:
    """Find the saved response for a key, or reject reuse for other input."""
    if not key:
        return None

    saved_experiment = session.scalar(
        select(Experiment).where(Experiment.idempotency_key == key)
    )
    if saved_experiment is None:
        return None

    saved_request = dict(saved_experiment.configuration)
    if experiment_type == AUTOMATIC:
        # These are outputs added after the request itself was accepted. They
        # must not make a retry with a blank seed look like a different input.
        saved_request.pop("resolved_seed", None)
        saved_request.pop("seed_was_generated", None)

    request_matches = (
        saved_experiment.experiment_type == experiment_type
        and saved_request == request
    )
    if not request_matches:
        raise HTTPException(
            status_code=409,
            detail="Idempotency-Key was already used for a different experiment request.",
        )
    return saved_experiment


def save_manual(
    session: Session,
    request: dict[str, Any],
    result: dict[str, Any],
    idempotency_key: str | None = None,
) -> Experiment:
    """Persist a completed manual auction, including all bidder outcomes."""
    experiment = Experiment(
        experiment_type=MANUAL,
        idempotency_key=idempotency_key,
        mechanism=request["mechanism"],
        strategy="Submitted bids",
        configuration={
            "mechanism": request["mechanism"],
            "valuations": request["valuations"],
            "bids": request["bids"],
            **({"click_through_rates": request["click_through_rates"]} if "click_through_rates" in request else {}),
        },
        result=result,
        metrics={
            "winner": result["winner"],
            "payment": result["payment"],
            "revenue": result["revenue"],
            "winner_payoff": result["winner_payoff"],
            **({
                "social_welfare": result["social_welfare"],
                "allocated_slots": sum(row.get("slot") is not None for row in result["advertisers"]),
            } if result.get("is_multi_slot") else {}),
        },
    )
    return _save_with_idempotency_recovery(
        session,
        experiment,
        idempotency_key,
        MANUAL,
        request,
    )


def save_simulation(
    session: Session,
    request: dict[str, Any],
    result: dict[str, Any],
    idempotency_key: str | None = None,
) -> Experiment:
    """Persist the request and aggregate result of a completed simulation."""
    profile_labels = [profile["label"] for profile in request["profiles"]]
    mechanisms = result["mechanisms"]
    mean_revenues = [
        block["revenue"]["mean"] for block in result["results"]
    ]
    mechanism_label = (
        "both" if mechanisms == ["first_price", "second_price"]
        else ",".join(mechanisms)
    )

    experiment = Experiment(
        experiment_type=AUTOMATIC,
        idempotency_key=idempotency_key,
        mechanism=mechanism_label,
        strategy="; ".join(profile_labels),
        configuration={
            **request,
            "resolved_seed": result["seed"],
            "seed_was_generated": result["seed_was_generated"],
        },
        result=result,
        metrics={
            "n_auctions": result["n_auctions"],
            "seed": result["seed"],
            "mean_revenue": mean_revenues,
            "profile_count": len(profile_labels),
            "result_count": len(result["results"]),
        },
    )
    return _save_with_idempotency_recovery(
        session,
        experiment,
        idempotency_key,
        AUTOMATIC,
        request,
    )


def _save_with_idempotency_recovery(
    session: Session,
    experiment: Experiment,
    idempotency_key: str | None,
    experiment_type: str,
    request: dict[str, Any],
) -> Experiment:
    """Commit once; if a concurrent retry wins, return that saved record."""
    session.add(experiment)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing_experiment = find_idempotent(
            session,
            idempotency_key,
            experiment_type,
            request,
        )
        if existing_experiment is not None:
            return existing_experiment
        raise

    session.refresh(experiment)
    return experiment


def summary(experiment: Experiment) -> dict[str, Any]:
    """Build the small record used in history lists."""
    return {
        "id": experiment.id,
        "created_at": _iso(experiment.created_at),
        "experiment_type": experiment.experiment_type,
        "mechanism": experiment.mechanism,
        "strategy": experiment.strategy,
        "metrics": experiment.metrics,
    }


def details(experiment: Experiment) -> dict[str, Any]:
    """Build the full history record, including saved inputs and outputs."""
    return {
        **summary(experiment),
        "configuration": experiment.configuration,
        "result": experiment.result,
    }


def list_experiments(
    session: Session,
    experiment_type: str | None = None,
    sort: str = "desc",
) -> tuple[list[Experiment], int]:
    """Return matching history rows and their total count."""
    query: Select[tuple[Experiment]] = select(Experiment)
    count_query = select(func.count()).select_from(Experiment)

    if experiment_type:
        query = query.where(Experiment.experiment_type == experiment_type)
        count_query = count_query.where(
            Experiment.experiment_type == experiment_type
        )

    date_order = (
        Experiment.created_at.asc()
        if sort == "asc"
        else Experiment.created_at.desc()
    )
    rows = list(
        session.scalars(query.order_by(date_order, Experiment.id)).all()
    )
    total_count = int(session.scalar(count_query) or 0)
    return rows, total_count


def overview_stats(session: Session) -> dict[str, Any]:
    """Return real saved-run counts and the five most recently created rows."""
    total_count = int(
        session.scalar(select(func.count()).select_from(Experiment)) or 0
    )
    manual_count = int(
        session.scalar(
            select(func.count())
            .select_from(Experiment)
            .where(Experiment.experiment_type == MANUAL)
        )
        or 0
    )
    automatic_count = int(
        session.scalar(
            select(func.count())
            .select_from(Experiment)
            .where(Experiment.experiment_type == AUTOMATIC)
        )
        or 0
    )
    most_recent = session.scalars(
        select(Experiment)
        .order_by(Experiment.created_at.desc(), Experiment.id)
        .limit(5)
    ).all()

    return {
        "total_experiments": total_count,
        "manual_auctions": manual_count,
        "automatic_simulations": automatic_count,
        "recent_experiments": [summary(item) for item in most_recent],
    }


def csv_content(experiment: Experiment) -> str:
    """Serialize one saved experiment as spreadsheet-friendly UTF-8 CSV."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)

    if experiment.experiment_type == MANUAL:
        _write_manual_csv(writer, experiment)
    else:
        _write_simulation_csv(writer, experiment)

    # The BOM helps spreadsheet programs recognize UTF-8 text correctly.
    return "\ufeff" + buffer.getvalue()


def _write_manual_csv(writer: Any, experiment: Experiment) -> None:
    """Write one CSV data row for each advertiser in a manual auction."""
    multi_slot = bool(experiment.result.get("is_multi_slot"))
    headers = ["experiment_id", "created_at", "mechanism", "advertiser", "valuation", "bid", "rank", "winner", "payment", "payoff"]
    if multi_slot:
        headers[4:6] = ["valuation_per_click", "bid_per_click"]
        headers.extend(["slot", "click_through_rate", "expected_value_per_impression", "payment_per_click", "expected_payment_per_impression", "expected_utility_per_impression"])
    writer.writerow(headers)
    for advertiser in experiment.result["advertisers"]:
        row = [
                experiment.id,
                _iso(experiment.created_at),
                experiment.mechanism,
                advertiser["advertiser"],
                advertiser["valuation"],
                advertiser["bid"],
                advertiser["rank"],
                advertiser["won"],
                advertiser["payment"],
                advertiser["payoff"],
            ]
        if multi_slot:
            row.extend([
                advertiser.get("slot"), advertiser.get("click_through_rate"),
                advertiser.get("expected_value"), advertiser.get("payment_per_click"),
                advertiser.get("expected_payment"), advertiser.get("expected_utility"),
            ])
        writer.writerow(row)


def _write_simulation_csv(writer: Any, experiment: Experiment) -> None:
    """Write one aggregate CSV row per saved profile/mechanism result."""
    writer.writerow(
        [
            "experiment_id", "created_at", "n_auctions", "seed",
            "seed_was_generated", "valuation_mode", "valuation_low",
            "valuation_high", "fixed_values", "mechanism", "strategy",
            "alphas", "mean_revenue", "revenue_median", "revenue_std",
            "revenue_se", "revenue_min", "revenue_max", "avg_winning_bid",
            "avg_winning_payment", "mean_winner_payoff", "mean_bidder_surplus",
            "highest_value_win_rate", "overbid_rate",
            "negative_winner_payoff_rate", "win_rate_A", "win_rate_B",
            "win_rate_C", "win_rate_D", "mean_payoff_A", "mean_payoff_B",
            "mean_payoff_C", "mean_payoff_D", "avg_expected_payment",
            "avg_total_expected_utility", "avg_social_welfare", "click_through_rates",
            "avg_ctr_A", "avg_ctr_B", "avg_ctr_C", "avg_ctr_D",
            "avg_payment_per_click_A", "avg_payment_per_click_B",
            "avg_payment_per_click_C", "avg_payment_per_click_D",
        ]
    )

    for result_block in experiment.result["results"]:
        revenue_stats = result_block["revenue"]
        valuation_settings = experiment.result["valuation"]
        writer.writerow(
            [
                experiment.id,
                _iso(experiment.created_at),
                experiment.result["n_auctions"],
                experiment.result["seed"],
                experiment.result["seed_was_generated"],
                valuation_settings.get("mode"),
                valuation_settings.get("low"),
                valuation_settings.get("high"),
                _json_cell(valuation_settings.get("fixed_values")),
                result_block["mechanism"],
                _safe_text(result_block["profile_label"]),
                _json_cell(result_block["alphas"]),
                revenue_stats["mean"],
                revenue_stats["median"],
                revenue_stats["std"],
                revenue_stats["se"],
                revenue_stats.get("min"),
                revenue_stats.get("max"),
                result_block.get("avg_winning_bid"),
                result_block.get("avg_winning_payment"),
                result_block["avg_winner_payoff"],
                result_block["avg_bidder_surplus"],
                result_block["highest_value_win_rate"],
                result_block["overbid_rate"],
                result_block["negative_winner_payoff_rate"],
                *(result_block["win_rate"][name] for name in "ABCD"),
                *(result_block["avg_payoff"][name] for name in "ABCD"),
                result_block.get("avg_expected_payment"),
                result_block.get("avg_total_expected_utility"),
                result_block.get("avg_social_welfare"),
                _json_cell(experiment.result.get("click_through_rates")),
                *(result_block.get("average_click_through_rate", {}).get(name) for name in "ABCD"),
                *(result_block.get("average_payment_per_click", {}).get(name) for name in "ABCD"),
            ]
        )


def _json_cell(value: Any) -> str:
    """Keep structured settings in one compact CSV cell."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _safe_text(value: str) -> str:
    """Prevent spreadsheet formula execution for exported strategy labels."""
    formula_prefixes = ("=", "+", "-", "@", "\t", "\r")
    return f"'{value}" if value.startswith(formula_prefixes) else value


def _iso(value: datetime) -> str:
    """Serialize database timestamps as ISO strings with a UTC offset."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
