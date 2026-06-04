"""ECB Open Data API client."""

from __future__ import annotations

import io
import logging
import time
from datetime import date

import httpx
import pandas as pd

from app.core.config import get_settings

logger = logging.getLogger(__name__)

BASE_URL = "https://data-api.ecb.europa.eu/service/data/EXR"


class ECBApiError(Exception):
    """Raised when the ECB API returns a non-success response after retries."""


async def fetch_exchange_rates(
    freq: str = "D",
    currency: str = "",
    start_period: date | None = None,
    end_period: date | None = None,
) -> pd.DataFrame:
    """
    Fetch exchange rate CSV data from the ECB API.

    Args:
        freq: Frequency code (e.g. 'D' for daily).
        currency: ISO currency code filter; empty string fetches all currencies.
        start_period: Inclusive start date for observations.
        end_period: Inclusive end date for observations.

    Returns:
        Raw DataFrame with columns including KEY, FREQ, CURRENCY, TIME_PERIOD,
        OBS_VALUE, and OBS_STATUS when present.
    """
    settings = get_settings()
    if start_period is None or end_period is None:
        raise ValueError("start_period and end_period are required")

    currency_segment = currency if currency else ""
    series_path = f"{freq}.{currency_segment}.EUR.SP00.A"
    url = f"{settings.ECB_BASE_URL}/{series_path}"
    params = {
        "startPeriod": start_period.isoformat(),
        "endPeriod": end_period.isoformat(),
        "format": "csvdata",
    }

    last_error: Exception | None = None
    for attempt in range(settings.ECB_RETRY_ATTEMPTS):
        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=settings.ECB_REQUEST_TIMEOUT) as client:
                response = await client.get(url, params=params)
            elapsed = time.perf_counter() - start_time

            if response.status_code == 200:
                df = _parse_csv_response(response.content)
                logger.info(
                    "ECB API request succeeded: url=%s status=%s elapsed=%.3fs rows=%d",
                    response.url,
                    response.status_code,
                    elapsed,
                    len(df),
                )
                return df

            if response.status_code in (429,) or response.status_code >= 500:
                wait_seconds = 2**attempt
                logger.warning(
                    "ECB API retryable error: url=%s status=%s attempt=%d wait=%ds",
                    response.url,
                    response.status_code,
                    attempt + 1,
                    wait_seconds,
                )
                last_error = ECBApiError(
                    f"ECB API returned status {response.status_code} for {response.url}"
                )
                if attempt < settings.ECB_RETRY_ATTEMPTS - 1:
                    await _sleep(wait_seconds)
                    continue
                raise last_error

            logger.error(
                "ECB API non-retryable error: url=%s status=%s elapsed=%.3fs",
                response.url,
                response.status_code,
                elapsed,
            )
            raise ECBApiError(
                f"ECB API returned status {response.status_code} for {response.url}"
            )
        except httpx.HTTPError as exc:
            elapsed = time.perf_counter() - start_time
            wait_seconds = 2**attempt
            logger.warning(
                "ECB API transport error: url=%s error=%s attempt=%d wait=%ds elapsed=%.3fs",
                url,
                exc,
                attempt + 1,
                wait_seconds,
                elapsed,
            )
            last_error = ECBApiError(f"ECB API transport error: {exc}")
            if attempt < settings.ECB_RETRY_ATTEMPTS - 1:
                await _sleep(wait_seconds)
                continue
            raise last_error from exc

    if last_error is not None:
        raise last_error
    raise ECBApiError("ECB API request failed after retries")


def _parse_csv_response(content: bytes) -> pd.DataFrame:
    """Parse ECB CSV bytes, skipping metadata comment lines."""
    text = content.decode("utf-8")
    lines = [line for line in text.splitlines() if not line.startswith("#")]
    cleaned = "\n".join(lines)
    return pd.read_csv(io.StringIO(cleaned))


async def _sleep(seconds: float) -> None:
    """Async sleep helper for retry backoff."""
    import asyncio

    await asyncio.sleep(seconds)
