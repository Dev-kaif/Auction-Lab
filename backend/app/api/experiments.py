from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_session
from app.experiments import csv_content, details, list_experiments, overview_stats, summary
from app.models import Experiment
from app.schemas.experiments import DeleteResult, ExperimentDetail, ExperimentList, OverviewStats

router = APIRouter(prefix="/api", tags=["experiments"])
ExperimentType = Literal["manual_auction", "automatic_simulation"]


@router.get("/experiments", response_model=ExperimentList, summary="List saved experiments")
def get_experiments(experiment_type: ExperimentType | None = Query(default=None), sort: Literal["asc", "desc"] = "desc",
                    session: Session = Depends(get_session)):
    rows, total = list_experiments(session, experiment_type, sort)
    return {"items": [summary(row) for row in rows], "total": total}


@router.get("/experiments/{experiment_id}", response_model=ExperimentDetail, summary="Get one saved experiment")
def get_experiment(experiment_id: str, session: Session = Depends(get_session)):
    experiment = session.get(Experiment, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return details(experiment)


@router.delete("/experiments/{experiment_id}", response_model=DeleteResult, summary="Delete a saved experiment")
def delete_experiment(experiment_id: str, session: Session = Depends(get_session)):
    experiment = session.get(Experiment, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    session.delete(experiment)
    session.commit()
    return {"deleted": True, "id": experiment_id}


@router.get("/experiments/{experiment_id}/csv", summary="Download experiment results as CSV")
def export_experiment(experiment_id: str, session: Session = Depends(get_session)):
    experiment = session.get(Experiment, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return Response(content=csv_content(experiment), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="auctionlab-{experiment.id}.csv"'})


@router.get("/overview", response_model=OverviewStats, summary="Get saved experiment counts and recent runs")
def overview(session: Session = Depends(get_session)):
    return overview_stats(session)
