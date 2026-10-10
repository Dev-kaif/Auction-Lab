from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.schemas.simulations import RunSimulationRequest, SimulationOut, SweepOut, SweepRequest
from app.simulation.runner import run_experiment, run_sweep
from app.db import get_session
from app.experiments import AUTOMATIC, find_idempotent, save_simulation

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post("/run", response_model=SimulationOut, summary="Run a repeated-auction simulation")
def run(req: RunSimulationRequest, session: Session = Depends(get_session),
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", min_length=1, max_length=64)] = None) -> dict:
    request = req.model_dump(mode="json")
    previous = find_idempotent(session, idempotency_key, AUTOMATIC, request)
    if previous is not None:
        return previous.result
    v = req.valuation
    result = run_experiment(
        n_auctions=req.n_auctions, mechanism=req.mechanism, mode=v.mode, low=v.low, high=v.high,
        fixed_values=v.fixed_values, seed=req.seed, profiles=[p.model_dump() for p in req.profiles])
    save_simulation(session, request, result, idempotency_key)
    return result


@router.post("/sweep", response_model=SweepOut, summary="Sweep a bidding fraction over a grid on shared valuations")
def sweep(req: SweepRequest) -> dict:
    return run_sweep(n_auctions=req.n_auctions, mechanism=req.mechanism, low=req.low, high=req.high,
                     seed=req.seed, mode=req.mode, deviator=req.deviator, others_alpha=req.others_alpha,
                     alphas=req.alphas)
