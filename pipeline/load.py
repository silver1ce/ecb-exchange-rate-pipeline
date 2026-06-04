"""Load stage: upsert observations into the OLTP database."""

from __future__ import annotations

import logging

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange_rate import (
    Currency,
    ExchangeRateObservation,
    ExchangeRateSeries,
    Frequency,
)
from pipeline.transform import FREQUENCY_DESCRIPTIONS, ObservationDTO

logger = logging.getLogger(__name__)


async def load_observations(
    session: AsyncSession,
    observations: list[ObservationDTO],
    run_id: int,  # noqa: ARG001 — reserved for future audit linkage
) -> tuple[int, int]:
    """
    Upsert frequency, currency, series, and observation rows in one transaction.

    Args:
        session: Active async SQLAlchemy session.
        observations: Validated observation DTOs.
        run_id: Ingestion run identifier for audit context.

    Returns:
        Tuple of (rows_inserted, rows_updated) for observations.
    """
    if not observations:
        return 0, 0

    rows_inserted = 0
    rows_updated = 0

    freq_cache: dict[str, int] = {}
    currency_cache: dict[str, int] = {}
    series_cache: dict[str, int] = {}

    for obs in observations:
        freq_id = await _upsert_frequency(session, obs.freq_code, freq_cache)
        currency_id = await _upsert_currency(session, obs.currency_code, currency_cache)
        series_id = await _upsert_series(
            session,
            obs,
            freq_id=freq_id,
            currency_id=currency_id,
            series_cache=series_cache,
        )
        inserted, updated = await _upsert_observation(session, obs, series_id)
        rows_inserted += inserted
        rows_updated += updated

    await session.flush()
    logger.info(
        "Load complete for run_id=%d: inserted=%d updated=%d",
        run_id,
        rows_inserted,
        rows_updated,
    )
    return rows_inserted, rows_updated


async def _upsert_frequency(
    session: AsyncSession,
    code: str,
    cache: dict[str, int],
) -> int:
    """Return frequency id, inserting lookup row when missing."""
    if code in cache:
        return cache[code]

    result = await session.execute(select(Frequency.id).where(Frequency.code == code))
    freq_id = result.scalar_one_or_none()
    if freq_id is None:
        frequency = Frequency(
            code=code,
            description=FREQUENCY_DESCRIPTIONS.get(code),
        )
        session.add(frequency)
        await session.flush()
        freq_id = frequency.id

    cache[code] = freq_id
    return freq_id


async def _upsert_currency(
    session: AsyncSession,
    iso_code: str,
    cache: dict[str, int],
) -> int:
    """Return currency id, inserting lookup row when missing."""
    if iso_code in cache:
        return cache[iso_code]

    result = await session.execute(select(Currency.id).where(Currency.iso_code == iso_code))
    currency_id = result.scalar_one_or_none()
    if currency_id is None:
        currency = Currency(iso_code=iso_code)
        session.add(currency)
        await session.flush()
        currency_id = currency.id

    cache[iso_code] = currency_id
    return currency_id


async def _upsert_series(
    session: AsyncSession,
    obs: ObservationDTO,
    *,
    freq_id: int,
    currency_id: int,
    series_cache: dict[str, int],
) -> int:
    """Return series id, inserting or updating metadata when needed."""
    if obs.series_key in series_cache:
        return series_cache[obs.series_key]

    result = await session.execute(
        select(ExchangeRateSeries.id).where(ExchangeRateSeries.series_key == obs.series_key)
    )
    series_id = result.scalar_one_or_none()
    if series_id is None:
        series = ExchangeRateSeries(
            series_key=obs.series_key,
            freq_id=freq_id,
            currency_id=currency_id,
            exr_type=obs.exr_type,
            exr_var=obs.exr_var,
        )
        session.add(series)
        await session.flush()
        series_id = series.id
    else:
        await session.execute(
            update(ExchangeRateSeries)
            .where(ExchangeRateSeries.id == series_id)
            .values(
                freq_id=freq_id,
                currency_id=currency_id,
                exr_type=obs.exr_type,
                exr_var=obs.exr_var,
                updated_at=func.now(),
            )
        )

    series_cache[obs.series_key] = series_id
    return series_id


async def _upsert_observation(
    session: AsyncSession,
    obs: ObservationDTO,
    series_id: int,
) -> tuple[int, int]:
    """Upsert a single observation using PostgreSQL ON CONFLICT."""
    existing = await session.execute(
        select(ExchangeRateObservation.id).where(
            ExchangeRateObservation.series_id == series_id,
            ExchangeRateObservation.time_period == obs.time_period,
        )
    )
    existed = existing.scalar_one_or_none() is not None

    bind = session.get_bind()
    dialect_name = bind.dialect.name if bind is not None else "postgresql"
    values = {
        "series_id": series_id,
        "time_period": obs.time_period,
        "obs_value": obs.obs_value,
        "obs_status": obs.obs_status,
    }
    conflict_update = {
        "obs_value": obs.obs_value,
        "obs_status": obs.obs_status,
        "updated_at": func.now(),
    }

    if dialect_name == "sqlite":
        sqlite_stmt = sqlite_insert(ExchangeRateObservation).values(**values)
        sqlite_stmt = sqlite_stmt.on_conflict_do_update(
            index_elements=["series_id", "time_period"],
            set_=conflict_update,
        )
        await session.execute(sqlite_stmt)
    else:
        pg_stmt = pg_insert(ExchangeRateObservation).values(**values)
        pg_stmt = pg_stmt.on_conflict_do_update(
            index_elements=["series_id", "time_period"],
            set_={
                "obs_value": pg_stmt.excluded.obs_value,
                "obs_status": pg_stmt.excluded.obs_status,
                "updated_at": func.now(),
            },
        )
        await session.execute(pg_stmt)

    if existed:
        return 0, 1
    return 1, 0

