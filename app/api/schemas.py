"""Pydantic schemas for REST API responses."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    db: str
    timestamp: datetime


class FrequencySchema(BaseModel):
    """Frequency lookup representation."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    description: str | None = None


class CurrencySchema(BaseModel):
    """Currency lookup representation."""

    model_config = ConfigDict(from_attributes=True)

    iso_code: str
    description: str | None = None


class SeriesResponse(BaseModel):
    """Exchange rate series with related lookup data."""

    model_config = ConfigDict(from_attributes=True)

    series_key: str
    exr_type: str | None = None
    exr_var: str | None = None
    description: str | None = None
    frequency: FrequencySchema
    currency: CurrencySchema


class ObservationResponse(BaseModel):
    """Single exchange rate observation."""

    model_config = ConfigDict(from_attributes=True)

    time_period: date
    obs_value: Decimal | None = None
    obs_status: str | None = None


class PaginatedObservationsResponse(BaseModel):
    """Paginated observations for a series."""

    series_key: str
    page: int
    size: int
    total: int
    items: list[ObservationResponse]


class LatestObservationResponse(BaseModel):
    """Most recent observation for a series."""

    series_key: str
    currency: str
    time_period: date
    obs_value: Decimal | None = None
    obs_status: str | None = None


class IngestRequest(BaseModel):
    """Manual ingestion trigger payload."""

    start_period: date
    end_period: date = Field(description="Inclusive end date for ingestion")


class IngestionRunResponse(BaseModel):
    """Ingestion run audit record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    rows_fetched: int | None = None
    rows_inserted: int | None = None
    rows_updated: int | None = None
    error_message: str | None = None
    api_url: str
    period_start: date
    period_end: date
