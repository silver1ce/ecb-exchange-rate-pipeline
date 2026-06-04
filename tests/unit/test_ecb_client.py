"""Unit tests for the ECB API client."""

from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.ecb_client import ECBApiError, fetch_exchange_rates

SAMPLE_CSV = """KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE
D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-01-02,1.0412
"""


@pytest.mark.asyncio
async def test_fetch_exchange_rates_success(ecb_sample_csv: str) -> None:
    """Successful API call returns parsed DataFrame."""
    response = httpx.Response(
        status_code=200,
        content=ecb_sample_csv.encode("utf-8"),
        request=httpx.Request("GET", "https://example.com"),
    )

    with patch("app.services.ecb_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = response
        mock_client_cls.return_value = mock_client

        df = await fetch_exchange_rates(
            start_period=date(2026, 1, 1),
            end_period=date(2026, 1, 31),
        )

    assert len(df) == 6
    assert "USD" in df["CURRENCY"].values


@pytest.mark.asyncio
async def test_fetch_exchange_rates_retries_on_429() -> None:
    """429 responses trigger retry with eventual success."""
    success_response = httpx.Response(
        status_code=200,
        content=SAMPLE_CSV.encode("utf-8"),
        request=httpx.Request("GET", "https://example.com"),
    )
    rate_limit_response = httpx.Response(
        status_code=429,
        content=b"rate limited",
        request=httpx.Request("GET", "https://example.com"),
    )

    with patch("app.services.ecb_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = [rate_limit_response, success_response]
        mock_client_cls.return_value = mock_client

        with patch("app.services.ecb_client._sleep", new_callable=AsyncMock):
            df = await fetch_exchange_rates(
                start_period=date(2026, 1, 1),
                end_period=date(2026, 1, 31),
            )

    assert len(df) == 1
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_exchange_rates_raises_after_max_retries() -> None:
    """ECBApiError is raised when retries are exhausted."""
    rate_limit_response = httpx.Response(
        status_code=429,
        content=b"rate limited",
        request=httpx.Request("GET", "https://example.com"),
    )

    with patch("app.services.ecb_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = rate_limit_response
        mock_client_cls.return_value = mock_client

        with (
            patch("app.services.ecb_client._sleep", new_callable=AsyncMock),
            pytest.raises(ECBApiError),
        ):
            await fetch_exchange_rates(
                start_period=date(2026, 1, 1),
                end_period=date(2026, 1, 31),
            )


@pytest.mark.asyncio
async def test_fetch_skips_csv_comment_lines() -> None:
    """Metadata comment lines prefixed with # are ignored."""
    csv_with_comments = "# Dataset: EXR\n# Updated: 2026-01-01\n" + SAMPLE_CSV
    response = httpx.Response(
        status_code=200,
        content=csv_with_comments.encode("utf-8"),
        request=httpx.Request("GET", "https://example.com"),
    )

    with patch("app.services.ecb_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = response
        mock_client_cls.return_value = mock_client

        df = await fetch_exchange_rates(
            start_period=date(2026, 1, 1),
            end_period=date(2026, 1, 31),
        )

    assert len(df) == 1
