"""Initialize local database tables (SQLite or PostgreSQL)."""

from __future__ import annotations

import asyncio
import logging

from app.core.database import Base, engine
from app.models import (  # noqa: F401 — register models with metadata
    Currency,
    ExchangeRateObservation,
    ExchangeRateSeries,
    Frequency,
    IngestionRun,
)

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create all ORM tables if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready.")


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_db())


if __name__ == "__main__":
    main()
