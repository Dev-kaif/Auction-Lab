from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.auctions.engine import run_auction
from app.auctions.explain import explain, formulas
from app.schemas.auctions import AuctionOut, RunAuctionRequest, to_out
from app.db import get_session
from app.experiments import MANUAL, find_idempotent, save_manual

router = APIRouter(prefix="/api/auctions", tags=["auctions"])


@router.post("/run", response_model=AuctionOut, summary="Run one manual auction")
def run(
    req: RunAuctionRequest,
    session: Session = Depends(get_session),
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=1, max_length=64)
    ] = None,
) -> AuctionOut:
    request = req.model_dump(mode="json")
    previous = find_idempotent(session, idempotency_key, MANUAL, request)
    
    if previous is not None:
        return AuctionOut.model_validate(previous.result)
    
    r = run_auction(req.valuations, req.bids, req.mechanism)
    output = to_out(r, explain(r), formulas(r.mechanism))
    
    save_manual(session, request, output.model_dump(mode="json"), idempotency_key)
    return output
