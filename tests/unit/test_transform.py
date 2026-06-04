"""Unit tests for ECB CSV transform logic."""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from pipeline.transform import (
    ObservationDTO,
    parse_obs_value,
    parse_time_period,
    transform_observations,
)


def test_parse_time_period_daily() -> None:
    """Daily TIME_PERIOD values parse to date objects."""
    assert parse_time_period("2026-01-15") == date(2026, 1, 15)


def test_parse_time_period_monthly() -> None:
    """Monthly TIME_PERIOD values normalize to first day of month."""
    assert parse_time_period("2026-01") == date(2026, 1, 1)


def test_parse_obs_value_missing_dot() -> None:
    """ECB missing marker '.' becomes None."""
    assert parse_obs_value(".") is None


def test_parse_obs_value_numeric() -> None:
    """Numeric strings convert to Decimal."""
    assert parse_obs_value("1.0412") == Decimal("1.0412")


def test_currency_extraction_from_key() -> None:
    """Currency code is extracted from KEY second segment."""
    df = pd.DataFrame(
        [
            {
                "KEY": "D.USD.EUR.SP00.A",
                "FREQ": "D",
                "CURRENCY": "USD",
                "EXR_TYPE": "SP00",
                "EXR_SUFFIX": "A",
                "TIME_PERIOD": "2026-01-02",
                "OBS_VALUE": "1.0412",
            }
        ]
    )
    observations = transform_observations(df)
    assert len(observations) == 1
    assert observations[0].currency_code == "USD"
    assert observations[0].exr_type == "SP00"
    assert observations[0].exr_var == "A"


def test_invalid_rows_are_skipped() -> None:
    """Invalid rows are skipped without raising."""
    df = pd.DataFrame(
        [
            {"KEY": "", "TIME_PERIOD": "2026-01-02", "OBS_VALUE": "1.0"},
            {
                "KEY": "D.USD.EUR.SP00.A",
                "FREQ": "D",
                "CURRENCY": "USD",
                "EXR_TYPE": "SP00",
                "EXR_SUFFIX": "A",
                "TIME_PERIOD": "2026-01-02",
                "OBS_VALUE": "1.0412",
            },
        ]
    )
    observations = transform_observations(df)
    assert len(observations) == 1
    assert isinstance(observations[0], ObservationDTO)


def test_parse_time_period_invalid_raises() -> None:
    """Unsupported TIME_PERIOD formats raise ValueError."""
    with pytest.raises(ValueError):
        parse_time_period("invalid")
