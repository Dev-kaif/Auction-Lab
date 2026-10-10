"""HTTP routes for single, manually configured auctions."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.auctions.engine import run_auction
from app.auctions.explain import explain, formulas
from app.db import get_session
from app.experiments import MANUAL, find_idempotent, save_manual
from app.schemas.auctions import AuctionOut, RunAuctionRequest, to_out

router = APIRouter(prefix="/api/auctions", tags=["auctions"])


@router.post("/run", response_model=AuctionOut, summary="Run one manual auction")
def run(
    request_body: RunAuctionRequest,
    session: Session = Depends(get_session),
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=1, max_length=64),
    ] = None,
) -> AuctionOut:
    """Calculate an auction and save its completed result."""
    request_data: dict[str, Any] = request_body.model_dump(mode="json", exclude_unset=True)

    # A retried request with the same key returns the original saved result.
    previous_experiment = find_idempotent(
        session,
        idempotency_key,
        MANUAL,
        request_data,
    )
    if previous_experiment is not None:
        return AuctionOut.model_validate(previous_experiment.result)

    auction_result = run_auction(
        request_body.valuations,
        request_body.bids,
        request_body.mechanism,
        request_body.click_through_rates,
    )
    response = to_out(
        auction_result,
        explain(auction_result),
        formulas(auction_result.mechanism),
    )

    save_manual(
        session,
        request_data,
        response.model_dump(mode="json"),
        idempotency_key,
    )
    return response
