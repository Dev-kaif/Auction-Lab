from typing import Any, Literal

from pydantic import BaseModel


class ExperimentSummary(BaseModel):
    id: str
    created_at: str
    experiment_type: Literal["manual_auction", "automatic_simulation"]
    mechanism: str
    strategy: str
    metrics: dict[str, Any]


class ExperimentDetail(ExperimentSummary):
    configuration: dict[str, Any]
    result: dict[str, Any]


class ExperimentList(BaseModel):
    items: list[ExperimentSummary]
    total: int


class OverviewStats(BaseModel):
    total_experiments: int
    manual_auctions: int
    automatic_simulations: int
    recent_experiments: list[ExperimentSummary]


class DeleteResult(BaseModel):
    deleted: bool
    id: str
