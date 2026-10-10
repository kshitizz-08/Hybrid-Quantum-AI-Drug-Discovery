"""
Database engine, session factory, and dependency injection helper.

SQLite is used for Milestone 1 (no Docker needed).
Switching to PostgreSQL only requires changing DATABASE_URL in .env.
"""
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Engine ────────────────────────────────────────────────────
# connect_args is required for SQLite (thread safety) but ignored by Postgres.
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug,  # SQL logging in debug mode
    pool_pre_ping=True,   # Verify connections before use
)

# Enable WAL mode for SQLite to allow concurrent reads during writes
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# ── Session Factory ───────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Base Class for ORM Models ─────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI Dependency ────────────────────────────────────────
def get_db():
    """Yield a database session and ensure it is closed after each request."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Create all tables. Called on application startup."""
    # Import models so SQLAlchemy registers them before create_all
    from app.models import base as _  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified.")


def check_db_connection() -> bool:
    """Test that the database is reachable. Returns True if OK."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database connection failed: %s", exc)
        return False
