"""Transform stage: parse and validate ECB CSV observations."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

FREQUENCY_DESCRIPTIONS: dict[str, str] = {
    "D": "Daily",
    "M": "Monthly",
    "Q": "Quarterly",
    "A": "Annual",
}


class ObservationDTO(BaseModel):
    """Validated observation ready for database loading."""

    series_key: str = Field(min_length=1, max_length=64)
    freq_code: str = Field(min_length=1, max_length=4)
    currency_code: str = Field(min_length=3, max_length=3)
    exr_type: str | None = Field(default=None, max_length=8)
    exr_var: str | None = Field(default=None, max_length=8)
    time_period: date
    obs_value: Decimal | None = None
    obs_status: str | None = Field(default=None, max_length=4)

    @field_validator("currency_code", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> str:
        """Normalize currency codes to uppercase."""
        return str(value).upper()


def transform_observations(df: pd.DataFrame) -> list[ObservationDTO]:
    """
    Parse and validate raw ECB DataFrame rows into ObservationDTO objects.

    Invalid rows are logged and skipped instead of raising.

    Args:
        df: Raw ECB API DataFrame.

    Returns:
        List of validated observation DTOs.
    """
    observations: list[ObservationDTO] = []
    if df.empty:
        return observations

    for index, row in df.iterrows():
        try:
            series_key = str(row.get("KEY", "")).strip()
            if not series_key:
                logger.warning("Skipping row %s: missing KEY", index)
                continue

            parts = series_key.split(".")
            if len(parts) < 5:
                logger.warning("Skipping row %s: invalid KEY format %s", index, series_key)
                continue

            freq_code = str(row.get("FREQ", parts[0])).strip()
            currency_code = str(row.get("CURRENCY", parts[1])).strip().upper()
            exr_type = str(row.get("EXR_TYPE", parts[3])).strip() or None
            exr_var = str(row.get("EXR_SUFFIX", parts[4])).strip() or None
            time_period = parse_time_period(str(row.get("TIME_PERIOD", "")).strip())
            obs_value = parse_obs_value(row.get("OBS_VALUE"))
            obs_status_raw = row.get("OBS_STATUS")
            obs_status = str(obs_status_raw).strip() if pd.notna(obs_status_raw) else None

            dto = ObservationDTO(
                series_key=series_key,
                freq_code=freq_code,
                currency_code=currency_code,
                exr_type=exr_type,
                exr_var=exr_var,
                time_period=time_period,
                obs_value=obs_value,
                obs_status=obs_status,
            )
            observations.append(dto)
        except Exception as exc:
            logger.warning("Skipping invalid row %s: %s", index, exc)
            continue

    return observations


def parse_time_period(value: str) -> date:
    """
    Parse ECB TIME_PERIOD values in YYYY-MM-DD or YYYY-MM format.

    Monthly values are normalized to the first day of the month.
    """
    if not value:
        raise ValueError("TIME_PERIOD is empty")

    if len(value) == 7 and value[4] == "-":
        year, month = value.split("-")
        return date(int(year), int(month), 1)

    if len(value) == 10 and value[4] == "-" and value[7] == "-":
        year, month, day = value.split("-")
        return date(int(year), int(month), int(day))

    raise ValueError(f"Unsupported TIME_PERIOD format: {value}")


def parse_obs_value(value: object) -> Decimal | None:
    """Convert ECB OBS_VALUE to Decimal, treating '.' as missing."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    text = str(value).strip()
    if text == "" or text == ".":
        return None

    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid OBS_VALUE: {value}") from exc
