"""SQLAlchemy ORM models for ECB exchange rate data."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Frequency(Base):
    """Lookup table for ECB data frequencies (D, M, Q, etc.)."""

    __tablename__ = "frequency"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(4), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    series: Mapped[list["ExchangeRateSeries"]] = relationship(back_populates="frequency")


class Currency(Base):
    """ISO 4217 currency codes referenced by exchange rate series."""

    __tablename__ = "currency"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    iso_code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    series: Mapped[list["ExchangeRateSeries"]] = relationship(back_populates="currency")


class ExchangeRateSeries(Base):
    """One row per unique ECB time series key."""

    __tablename__ = "exchange_rate_series"
    __table_args__ = (
        Index("idx_series_currency", "currency_id"),
        Index("idx_series_freq", "freq_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    freq_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("frequency.id"),
        nullable=False,
    )
    currency_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("currency.id"),
        nullable=False,
    )
    exr_type: Mapped[str | None] = mapped_column(String(8))
    exr_var: Mapped[str | None] = mapped_column(String(8))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    frequency: Mapped["Frequency"] = relationship(back_populates="series")
    currency: Mapped["Currency"] = relationship(back_populates="series")
    observations: Mapped[list["ExchangeRateObservation"]] = relationship(
        back_populates="series",
    )


class ExchangeRateObservation(Base):
    """One observation per series and time period."""

    __tablename__ = "exchange_rate_observation"
    __table_args__ = (
        UniqueConstraint("series_id", "time_period", name="uq_obs_series_period"),
        Index("idx_obs_series_period", "series_id", "time_period"),
        Index("idx_obs_time_period", "time_period"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("exchange_rate_series.id"),
        nullable=False,
    )
    time_period: Mapped[date] = mapped_column(Date, nullable=False)
    obs_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    obs_status: Mapped[str | None] = mapped_column(String(4))
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    series: Mapped["ExchangeRateSeries"] = relationship(back_populates="observations")


class IngestionRun(Base):
    """Audit log for pipeline executions."""

    __tablename__ = "ingestion_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    rows_fetched: Mapped[int | None] = mapped_column(Integer)
    rows_inserted: Mapped[int | None] = mapped_column(Integer)
    rows_updated: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    api_url: Mapped[str] = mapped_column(Text, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
