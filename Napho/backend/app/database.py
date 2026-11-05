from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# ---------------------------------------------------------------------------
# Engine — SQLite with WAL mode + foreign key enforcement
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """Yield a database session and close it when the request is finished."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Table creation helper (used by seed script and tests)
# ---------------------------------------------------------------------------
def init_db() -> None:
    """Create all tables that have been registered with the metadata."""
    # Import models so that SQLAlchemy metadata is populated before create_all
    import app.models  # noqa: F401  # side-effect import

    from app.models.base import Base

    Base.metadata.create_all(bind=engine)
