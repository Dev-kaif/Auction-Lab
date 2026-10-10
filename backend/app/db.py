"""SQLAlchemy engine, session factory, and SQLite initialization helpers."""

from collections.abc import Generator
from threading import Lock

from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Base class used by the database models."""


def make_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine with SQLite's thread check disabled."""
    connection_options = (
        {"check_same_thread": False}
        if database_url.startswith("sqlite:")
        else {}
    )
    return create_engine(
        database_url,
        connect_args=connection_options,
        pool_pre_ping=True,
    )


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

_database_initialized = False
_initialization_lock = Lock()


def _upgrade_sqlite_idempotency_column(database_engine: Engine) -> None:
    """Add the idempotency key to databases created before that field existed."""
    inspector = inspect(database_engine)
    existing_columns = {
        column["name"]
        for column in inspector.get_columns("experiments")
    }
    if "idempotency_key" not in existing_columns:
        with database_engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE experiments ADD COLUMN idempotency_key VARCHAR(64)"
            )

    # Older SQLite databases need a unique index because the old table did not
    # have the model's unique constraint. SQLite allows multiple NULL keys.
    unique_columns = [
        constraint.get("column_names")
        for constraint in inspector.get_unique_constraints("experiments")
    ]
    if ["idempotency_key"] not in unique_columns:
        with database_engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "ix_experiments_idempotency_key "
                "ON experiments (idempotency_key)"
            )


def initialize_database(target_engine: Engine | None = None) -> None:
    """Create missing tables and apply the small SQLite compatibility upgrade.

    A supplied engine is initialized independently. This is useful for tests
    that build a temporary database without changing the application's engine.
    """
    global _database_initialized

    # Importing the mapped class registers its table with Base.metadata.
    from app.models import Experiment  # noqa: F401

    database_engine = target_engine or engine
    if target_engine is not None:
        Base.metadata.create_all(bind=database_engine)
        return

    if _database_initialized:
        return

    with _initialization_lock:
        if _database_initialized:
            return

        Base.metadata.create_all(bind=database_engine)
        if database_engine.dialect.name == "sqlite":
            _upgrade_sqlite_idempotency_column(database_engine)
        _database_initialized = True


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields one session and always closes it."""
    initialize_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
