"""HTTP routes for repeated simulations and strategy sweeps."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db import get_session
from app.experiments import AUTOMATIC, find_idempotent, save_simulation
from app.schemas.simulations import (
    RunSimulationRequest,
    SimulationOut,
    SweepOut,
    SweepRequest,
)
from app.simulation.runner import run_experiment, run_sweep

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post("/run", response_model=SimulationOut, summary="Run a repeated-auction simulation")
def run(
    request_body: RunSimulationRequest,
    session: Session = Depends(get_session),
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=1, max_length=64),
    ] = None,
) -> dict[str, Any]:
    """Run selected profiles and mechanisms, then persist their aggregates."""
    request_data = request_body.model_dump(mode="json")
    # Keep retries compatible with saved runs created before CTR settings
    # became part of the request contract; the engine supplies the same default.
    if "click_through_rates" not in request_body.model_fields_set:
        request_data.pop("click_through_rates", None)

    # Return the stored response for a safely retried request.
    previous_experiment = find_idempotent(
        session,
        idempotency_key,
        AUTOMATIC,
        request_data,
    )
    if previous_experiment is not None:
        return previous_experiment.result

    valuation_settings = request_body.valuation
    result = run_experiment(
        n_auctions=request_body.n_auctions,
        mechanism=request_body.mechanism,
        mode=valuation_settings.mode,
        low=valuation_settings.low,
        high=valuation_settings.high,
        fixed_values=valuation_settings.fixed_values,
        seed=request_body.seed,
        profiles=[profile.model_dump() for profile in request_body.profiles],
        click_through_rates=request_body.click_through_rates,
    )

    save_simulation(session, request_data, result, idempotency_key)
    return result


@router.post(
    "/sweep",
    response_model=SweepOut,
    summary="Sweep a bidding fraction over a grid on shared valuations",
)
def sweep(request_body: SweepRequest) -> dict[str, Any]:
    """Evaluate strategy fractions against the same generated valuations."""
    return run_sweep(
        n_auctions=request_body.n_auctions,
        mechanism=request_body.mechanism,
        low=request_body.low,
        high=request_body.high,
        seed=request_body.seed,
        mode=request_body.mode,
        deviator=request_body.deviator,
        others_alpha=request_body.others_alpha,
        alphas=request_body.alphas,
        click_through_rates=request_body.click_through_rates,
    )
