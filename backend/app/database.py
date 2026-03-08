import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import DATABASE_URL

logger = logging.getLogger(__name__)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _run_migrations():
    """Add columns that may be missing from older schemas."""
    inspector = inspect(engine)
    migrations: list[str] = []

    if inspector.has_table("stock_signals"):
        cols = {c["name"] for c in inspector.get_columns("stock_signals")}
        if "signal_type" not in cols:
            migrations.append(
                "ALTER TABLE stock_signals ADD COLUMN signal_type VARCHAR(10) DEFAULT 'bullish'"
            )
        for col_name, col_def in [
            ("revenue_growth", "FLOAT"),
            ("operating_margin", "FLOAT"),
            ("operating_cashflow", "BIGINT DEFAULT 0"),
            ("free_cashflow", "BIGINT DEFAULT 0"),
            ("ps_ratio", "FLOAT"),
            ("pb_ratio", "FLOAT"),
            ("weekly_sma30", "FLOAT"),
            ("above_weekly_sma", "BOOLEAN"),
        ]:
            if col_name not in cols:
                migrations.append(
                    f"ALTER TABLE stock_signals ADD COLUMN {col_name} {col_def}"
                )

    if migrations:
        with engine.begin() as conn:
            for stmt in migrations:
                logger.info("Running migration: %s", stmt)
                conn.execute(text(stmt))


def init_db():
    Base.metadata.create_all(bind=engine)
    _run_migrations()
