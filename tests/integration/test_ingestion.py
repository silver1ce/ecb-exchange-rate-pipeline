"""Integration tests for the full ingestion pipeline."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
from sqlalchemy import func, select

from app.models.exchange_rate import ExchangeRateObservation, IngestionRun
from app.services.ingestion import run_ingestion


@pytest.mark.asyncio
async def test_full_ingestion_with_mocked_api(db_session, ecb_sample_csv: str) -> None:
    """Full ETL inserts expected observation rows."""
    mock_df = pd.read_csv(pd.io.common.StringIO(ecb_sample_csv))

    with patch("pipeline.extract.fetch_exchange_rates", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_df
        run = await run_ingestion(
            db_session,
            start_period=date(2026, 1, 1),
            end_period=date(2026, 1, 31),
        )

    assert run.status == "success"
    assert run.rows_fetched == 6

    count = await db_session.scalar(select(func.count()).select_from(ExchangeRateObservation))
    assert count == 6


@pytest.mark.asyncio
async def test_ingestion_upsert_is_idempotent(db_session, ecb_sample_csv: str) -> None:
    """Running ingestion twice does not duplicate observations."""
    mock_df = pd.read_csv(pd.io.common.StringIO(ecb_sample_csv))

    with patch("pipeline.extract.fetch_exchange_rates", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_df
        await run_ingestion(db_session, date(2026, 1, 1), date(2026, 1, 31))
        await run_ingestion(db_session, date(2026, 1, 1), date(2026, 1, 31))

    obs_count = await db_session.scalar(
        select(func.count()).select_from(ExchangeRateObservation)
    )
    run_count = await db_session.scalar(select(func.count()).select_from(IngestionRun))

    assert obs_count == 6
    assert run_count == 2


@pytest.mark.asyncio
async def test_ingestion_marks_run_failed_on_error(db_session) -> None:
    """Failed ingestion updates run status and re-raises."""
    with patch("pipeline.extract.fetch_exchange_rates", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = RuntimeError("API unavailable")
        with pytest.raises(RuntimeError):
            await run_ingestion(db_session, date(2026, 1, 1), date(2026, 1, 31))

    run = (await db_session.execute(select(IngestionRun))).scalar_one()
    assert run.status == "failed"
    assert run.error_message == "API unavailable"
