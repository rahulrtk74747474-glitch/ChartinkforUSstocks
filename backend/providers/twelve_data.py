"""Twelve Data adapter used by the scanner.

Keep provider-specific API calls in this module so scanner formulas do not
need to know which vendor supplied the prices.
"""

import os
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from twelvedata import TDClient

load_dotenv()


def get_client() -> TDClient:
    """Create an authenticated client using the environment variable."""
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key or api_key.strip() in {"", "replace_me", "YOUR_API_KEY"}:
        raise RuntimeError(
            "TWELVE_DATA_API_KEY is missing. Set it in your local .env file "
            "or in the runtime environment."
        )
    return TDClient(apikey=api_key.strip())


def get_daily_prices(
    symbol: str,
    outputsize: int = 100,
    exchange: Optional[str] = None,
    interval: str = "1day",
) -> pd.DataFrame:
    """Fetch daily OHLCV history and return a chronological DataFrame.

    Args:
        symbol: Instrument ticker (for example, AAPL).
        outputsize: Number of daily bars requested; subject to plan limits.
        exchange: Optional exchange identifier supported by Twelve Data.

    Returns:
        DataFrame indexed by timestamp, oldest row first. Column names are
        lowercase when supplied by the provider.

    Raises:
        ValueError: Invalid input or no usable rows returned.
        RuntimeError: API key is not configured.
    """
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("A non-empty stock symbol is required.")
    if not isinstance(outputsize, int) or outputsize < 2:
        raise ValueError("outputsize must be an integer of at least 2.")

    allowed_intervals = {"1min", "5min", "15min", "30min", "45min", "1h", "2h", "4h", "1day", "1week", "1month"}
    if interval not in allowed_intervals:
        raise ValueError(f"Unsupported interval: {interval}")

    params = {
        "symbol": symbol.strip(),
        "interval": interval,
        "outputsize": outputsize,
        "timezone": "Exchange",
    }
    if exchange:
        params["exchange"] = exchange

    try:
        frame = get_client().time_series(**params).as_pandas()
    except Exception as exc:
        # Do not include the provider exception text: some SDK errors may
        # contain request URLs, which can include credentials.
        raise RuntimeError(
            f"Twelve Data request failed ({type(exc).__name__}). Check the API "
            "key, symbol/exchange, endpoint access, and remaining credits."
        ) from None

    if frame is None or frame.empty:
        raise ValueError(f"Twelve Data returned no daily rows for {symbol}.")

    frame = frame.copy()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame.loc[~frame.index.isna()]
    frame = frame.sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]

    for column in ("open", "high", "low", "close", "volume"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if frame.empty or "close" not in frame.columns:
        raise ValueError(
            f"Twelve Data returned no usable close-price history for {symbol}."
        )
    return frame
