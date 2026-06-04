"""Ingestion orchestration service."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.exchange_rate import IngestionRun
from pipeline.extract import extract
from pipeline.load import load_observations
from pipeline.transform import transform_observations

logger = logging.getLogger(__name__)


def _build_api_url(start_period: date, end_period: date) -> str:
    """Build the ECB API URL used for an ingestion run."""
    settings = get_settings()
    return (
        f"{settings.ECB_BASE_URL}/D..EUR.SP00.A"
        f"?startPeriod={start_period.isoformat()}"
        f"&endPeriod={end_period.isoformat()}&format=csvdata"
    )


async def run_ingestion(
    session: AsyncSession,
    start_period: date,
    end_period: date,
    *,
    freq: str = "D",
    currency: str = "",
) -> IngestionRun:
    """
    Execute the full ETL pipeline and record an ingestion_run audit row.

    Args:
        session: Async database session.
        start_period: Inclusive start date.
        end_period: Inclusive end date.
        freq: ECB frequency code.
        currency: Optional currency filter.

    Returns:
        Completed ingestion run record.

    Raises:
        Exception: Re-raises any pipeline failure after marking the run failed.
    """
    api_url = _build_api_url(start_period, end_period)
    run = IngestionRun(
        status="running",
        api_url=api_url,
        period_start=start_period,
        period_end=end_period,
    )
    session.add(run)
    await session.flush()

    try:
        raw_df = await extract(
            start_period=start_period,
            end_period=end_period,
            freq=freq,
            currency=currency,
        )
        observations = transform_observations(raw_df)
        rows_inserted, rows_updated = await load_observations(session, observations, run.id)

        run.status = "success"
        run.finished_at = datetime.now(UTC)
        run.rows_fetched = len(raw_df)
        run.rows_inserted = rows_inserted
        run.rows_updated = rows_updated
        await session.flush()
        logger.info(
            "Ingestion run %d succeeded: fetched=%d inserted=%d updated=%d",
            run.id,
            run.rows_fetched,
            run.rows_inserted,
            run.rows_updated,
        )
        return run
    except Exception as exc:
        run.status = "failed"
        run.finished_at = datetime.now(UTC)
        run.error_message = str(exc)
        await session.flush()
        logger.exception("Ingestion run %d failed", run.id)
        raise
