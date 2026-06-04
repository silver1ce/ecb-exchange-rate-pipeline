"""Extract stage: fetch raw data from the ECB API."""

from datetime import date

import pandas as pd

from app.services.ecb_client import fetch_exchange_rates


async def extract(
    start_period: date,
    end_period: date,
    freq: str = "D",
    currency: str = "",
) -> pd.DataFrame:
    """
    Extract exchange rate observations from the ECB API.

    Args:
        start_period: Inclusive start date.
        end_period: Inclusive end date.
        freq: Frequency code.
        currency: Optional currency filter.

    Returns:
        Raw DataFrame from the ECB API.
    """
    return await fetch_exchange_rates(
        freq=freq,
        currency=currency,
        start_period=start_period,
        end_period=end_period,
    )
