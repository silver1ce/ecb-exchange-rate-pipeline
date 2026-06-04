"""Integration tests for REST API endpoints."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange_rate import (
    Currency,
    ExchangeRateObservation,
    ExchangeRateSeries,
    Frequency,
)
from app.services.ingestion import run_ingestion


async def _seed_series(db_session: AsyncSession) -> None:
    """Insert sample series and observations for API tests."""
    frequency = Frequency(code="D", description="Daily")
    currency = Currency(iso_code="USD")
    db_session.add_all([frequency, currency])
    await db_session.flush()

    series = ExchangeRateSeries(
        series_key="D.USD.EUR.SP00.A",
        freq_id=frequency.id,
        currency_id=currency.id,
        exr_type="SP00",
        exr_var="A",
    )
    db_session.add(series)
    await db_session.flush()

    observation = ExchangeRateObservation(
        series_id=series.id,
        time_period=date(2026, 1, 2),
        obs_value=Decimal("1.0412"),
        obs_status="A",
    )
    db_session.add(observation)
    await db_session.flush()


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient, db_session: AsyncSession) -> None:
    """Health endpoint returns 200 when database is reachable."""
    response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["db"] == "ok"


@pytest.mark.asyncio
async def test_list_series(client: AsyncClient, db_session: AsyncSession) -> None:
    """Series endpoint returns seeded series."""
    await _seed_series(db_session)
    response = await client.get("/api/v1/series?currency=USD&freq=D")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["series_key"] == "D.USD.EUR.SP00.A"
    assert data[0]["currency"]["iso_code"] == "USD"


@pytest.mark.asyncio
async def test_list_observations(client: AsyncClient, db_session: AsyncSession) -> None:
    """Observations endpoint returns paginated results."""
    await _seed_series(db_session)
    response = await client.get(
        "/api/v1/series/D.USD.EUR.SP00.A/observations?start=2026-01-01&end=2026-01-31"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert Decimal(data["items"][0]["obs_value"]) == Decimal("1.0412")


@pytest.mark.asyncio
async def test_latest_observations(client: AsyncClient, db_session: AsyncSession) -> None:
    """Latest observations endpoint returns most recent values."""
    await _seed_series(db_session)
    response = await client.get("/api/v1/observations/latest?currency=USD")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["currency"] == "USD"


@pytest.mark.asyncio
async def test_trigger_ingest(
    client: AsyncClient, db_session: AsyncSession, ecb_sample_csv: str
) -> None:
    """Manual ingest endpoint runs pipeline and returns run record."""
    mock_df = pd.read_csv(pd.io.common.StringIO(ecb_sample_csv))

    with patch("pipeline.extract.fetch_exchange_rates", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_df
        response = await client.post(
            "/api/v1/ingest",
            json={"start_period": "2026-01-01", "end_period": "2026-01-31"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["rows_fetched"] == 6


@pytest.mark.asyncio
async def test_list_ingestion_runs(
    client: AsyncClient, db_session: AsyncSession, ecb_sample_csv: str
) -> None:
    """Ingestion runs endpoint lists recent runs."""
    mock_df = pd.read_csv(pd.io.common.StringIO(ecb_sample_csv))

    with patch("pipeline.extract.fetch_exchange_rates", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_df
        await run_ingestion(db_session, date(2026, 1, 1), date(2026, 1, 31))

    response = await client.get("/api/v1/ingestion-runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["status"] == "success"


@pytest.mark.asyncio
async def test_series_not_found(client: AsyncClient) -> None:
    """Unknown series key returns 404."""
    response = await client.get("/api/v1/series/UNKNOWN/observations")
    assert response.status_code == 404
