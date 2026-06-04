"""Historical backfill script for ECB exchange rate data."""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date, timedelta

from app.core.database import async_session_factory
from app.services.ingestion import run_ingestion

logger = logging.getLogger(__name__)


async def _backfill(start_period: date, end_period: date, chunk_days: int) -> None:
    """Backfill data in configurable date chunks."""
    current = start_period
    while current <= end_period:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end_period)
        logger.info("Backfilling %s to %s", current.isoformat(), chunk_end.isoformat())
        async with async_session_factory() as session:
            run = await run_ingestion(session, current, chunk_end)
            await session.commit()
            logger.info(
                "Chunk complete: run_id=%s status=%s rows_inserted=%s",
                run.id,
                run.status,
                run.rows_inserted,
            )
        current = chunk_end + timedelta(days=1)


def main() -> None:
    """CLI entry point for historical backfill."""
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Backfill ECB exchange rate history")
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    parser.add_argument("--chunk-days", type=int, default=31, help="Days per API request chunk")
    args = parser.parse_args()

    if args.end < args.start:
        raise SystemExit("end date must be >= start date")

    asyncio.run(_backfill(args.start, args.end, args.chunk_days))


if __name__ == "__main__":
    main()
