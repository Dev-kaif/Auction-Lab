from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Experiment(Base):
    __tablename__ = "experiments"
    __table_args__ = (Index("ix_experiments_type_created", "experiment_type", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                                                 server_default=func.now(), nullable=False)
    experiment_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    mechanism: Mapped[str] = mapped_column(String(24), nullable=False)
    strategy: Mapped[str] = mapped_column(String(600), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

