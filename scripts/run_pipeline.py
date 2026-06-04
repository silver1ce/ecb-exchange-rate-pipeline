"""Manual pipeline trigger script."""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date, timedelta

from app.core.database import async_session_factory
from app.services.ingestion import run_ingestion

logger = logging.getLogger(__name__)


async def _run(start_period: date, end_period: date) -> None:
    """Execute ingestion for the given date range."""
    async with async_session_factory() as session:
        run = await run_ingestion(session, start_period, end_period)
        await session.commit()
        logger.info(
            "Pipeline complete: run_id=%s status=%s inserted=%s updated=%s",
            run.id,
            run.status,
            run.rows_inserted,
            run.rows_updated,
        )


def main() -> None:
    """CLI entry point for manual pipeline execution."""
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Run ECB exchange rate ingestion pipeline")
    parser.add_argument("--start", type=date.fromisoformat, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=date.fromisoformat, help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    end_period = args.end or date.today()
    start_period = args.start or (end_period - timedelta(days=7))

    asyncio.run(_run(start_period, end_period))


if __name__ == "__main__":
    main()
