"""FastAPI route definitions for the exchange rate API."""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    HealthResponse,
    IngestionRunResponse,
    IngestRequest,
    LatestObservationResponse,
    ObservationResponse,
    PaginatedObservationsResponse,
    SeriesResponse,
)
from app.core.database import get_db_session
from app.models.exchange_rate import (
    Currency,
    ExchangeRateObservation,
    ExchangeRateSeries,
    Frequency,
    IngestionRun,
)
from app.services.ingestion import run_ingestion

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check(session: AsyncSession = Depends(get_db_session)) -> HealthResponse:
    """Return service and database connectivity status."""
    db_status = "ok"
    try:
        await session.execute(select(1))
    except Exception:
        db_status = "error"
    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        db=db_status,
        timestamp=datetime.now(UTC),
    )


@router.get("/api/v1/series", response_model=list[SeriesResponse], tags=["series"])
async def list_series(
    currency: str | None = Query(default=None, description="Filter by ISO currency code"),
    freq: str | None = Query(default=None, description="Filter by frequency code"),
    session: AsyncSession = Depends(get_db_session),
) -> list[SeriesResponse]:
    """List exchange rate series with optional currency and frequency filters."""
    stmt = select(ExchangeRateSeries).options(
        selectinload(ExchangeRateSeries.frequency),
        selectinload(ExchangeRateSeries.currency),
    )
    if currency:
        stmt = stmt.join(Currency).where(Currency.iso_code == currency.upper())
    if freq:
        stmt = stmt.join(Frequency).where(Frequency.code == freq.upper())

    result = await session.execute(stmt.order_by(ExchangeRateSeries.series_key))
    series_list = result.scalars().all()
    return [SeriesResponse.model_validate(item) for item in series_list]


@router.get(
    "/api/v1/series/{series_key}/observations",
    response_model=PaginatedObservationsResponse,
    tags=["observations"],
)
async def list_observations(
    series_key: str,
    start: date | None = Query(default=None, description="Inclusive start date"),
    end: date | None = Query(default=None, description="Inclusive end date"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
) -> PaginatedObservationsResponse:
    """Return paginated observations for a series."""
    series_result = await session.execute(
        select(ExchangeRateSeries.id).where(ExchangeRateSeries.series_key == series_key)
    )
    series_id = series_result.scalar_one_or_none()
    if series_id is None:
        raise HTTPException(status_code=404, detail=f"Series not found: {series_key}")

    filters = [ExchangeRateObservation.series_id == series_id]
    if start is not None:
        filters.append(ExchangeRateObservation.time_period >= start)
    if end is not None:
        filters.append(ExchangeRateObservation.time_period <= end)

    count_stmt = select(func.count()).select_from(ExchangeRateObservation).where(*filters)
    total = int((await session.execute(count_stmt)).scalar_one())

    offset = (page - 1) * size
    obs_stmt = (
        select(ExchangeRateObservation)
        .where(*filters)
        .order_by(ExchangeRateObservation.time_period.desc())
        .offset(offset)
        .limit(size)
    )
    observations = (await session.execute(obs_stmt)).scalars().all()

    return PaginatedObservationsResponse(
        series_key=series_key,
        page=page,
        size=size,
        total=total,
        items=[ObservationResponse.model_validate(obs) for obs in observations],
    )


@router.get(
    "/api/v1/observations/latest",
    response_model=list[LatestObservationResponse],
    tags=["observations"],
)
async def latest_observations(
    currency: str | None = Query(default=None, description="Filter by ISO currency code"),
    session: AsyncSession = Depends(get_db_session),
) -> list[LatestObservationResponse]:
    """Return the most recent observation per series."""
    latest_subq = (
        select(
            ExchangeRateObservation.series_id,
            func.max(ExchangeRateObservation.time_period).label("max_period"),
        )
        .group_by(ExchangeRateObservation.series_id)
        .subquery()
    )

    stmt = (
        select(ExchangeRateObservation, ExchangeRateSeries, Currency)
        .join(ExchangeRateSeries, ExchangeRateObservation.series_id == ExchangeRateSeries.id)
        .join(Currency, ExchangeRateSeries.currency_id == Currency.id)
        .join(
            latest_subq,
            (ExchangeRateObservation.series_id == latest_subq.c.series_id)
            & (ExchangeRateObservation.time_period == latest_subq.c.max_period),
        )
    )
    if currency:
        stmt = stmt.where(Currency.iso_code == currency.upper())

    rows = (await session.execute(stmt.order_by(ExchangeRateSeries.series_key))).all()
    return [
        LatestObservationResponse(
            series_key=series.series_key,
            currency=currency_row.iso_code,
            time_period=observation.time_period,
            obs_value=observation.obs_value,
            obs_status=observation.obs_status,
        )
        for observation, series, currency_row in rows
    ]


@router.post(
    "/api/v1/ingest",
    response_model=IngestionRunResponse,
    tags=["ingestion"],
)
async def trigger_ingestion(
    payload: IngestRequest,
    session: AsyncSession = Depends(get_db_session),
) -> IngestionRunResponse:
    """Trigger a manual ingestion run for the given date range."""
    if payload.end_period < payload.start_period:
        raise HTTPException(status_code=400, detail="end_period must be >= start_period")

    run = await run_ingestion(session, payload.start_period, payload.end_period)
    return IngestionRunResponse.model_validate(run)


@router.get(
    "/api/v1/ingestion-runs",
    response_model=list[IngestionRunResponse],
    tags=["ingestion"],
)
async def list_ingestion_runs(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> list[IngestionRunResponse]:
    """List recent ingestion runs ordered by start time descending."""
    stmt = (
        select(IngestionRun)
        .order_by(IngestionRun.started_at.desc())
        .limit(limit)
    )
    runs = (await session.execute(stmt)).scalars().all()
    return [IngestionRunResponse.model_validate(run) for run in runs]
