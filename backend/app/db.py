from collections.abc import Generator
from threading import Lock

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    kwargs = {"check_same_thread": False} if url.startswith("sqlite:") else {}
    return create_engine(url, connect_args=kwargs, pool_pre_ping=True)


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
_initialized = False
_initialize_lock = Lock()


def initialize_database(target_engine=None) -> None:
    global _initialized
    from app.models import Experiment  # noqa: F401 - register mapped model metadata

    bind = target_engine or engine
    if target_engine is not None:
        Base.metadata.create_all(bind=bind)
        return
    if _initialized:
        return
    with _initialize_lock:
        if not _initialized:
            Base.metadata.create_all(bind=bind)
            if bind.dialect.name == "sqlite":
                inspector = inspect(bind)
                columns = {column["name"] for column in inspector.get_columns("experiments")}
                if "idempotency_key" not in columns:
                    with bind.begin() as connection:
                        connection.exec_driver_sql("ALTER TABLE experiments ADD COLUMN idempotency_key VARCHAR(64)")
                unique_columns = [constraint.get("column_names") for constraint in inspector.get_unique_constraints("experiments")]
                if ["idempotency_key"] not in unique_columns:
                    with bind.begin() as connection:
                        connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS ix_experiments_idempotency_key ON experiments (idempotency_key)")
            _initialized = True


def get_session() -> Generator[Session, None, None]:
    initialize_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
