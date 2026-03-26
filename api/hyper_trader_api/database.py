"""
Database connection and session management for HyperTrader API.

Uses SQLAlchemy 2.0 style with database-specific configuration:
- SQLite: Uses check_same_thread=False for FastAPI async compatibility, StaticPool
- PostgreSQL: Uses connection pooling for production workloads
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from hyper_trader_api.config import get_settings

# Get settings
settings = get_settings()

# Create engine with database-specific configuration
if settings.database_url.startswith("sqlite"):
    # SQLite configuration for self-hosted deployment
    # Use StaticPool to avoid QueuePool threading issues
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
else:
    # PostgreSQL configuration (if ever needed in future)
    from sqlalchemy.pool import QueuePool

    engine = create_engine(
        settings.database_url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    All models should inherit from this class to be included
    in database migrations and schema creation.
    """

    pass


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database session.

    Yields a database session and ensures it is closed after use.
    Use with FastAPI's Depends():

        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    Yields:
        Session: SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
