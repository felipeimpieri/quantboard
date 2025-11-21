"""Data access helpers for price downloads."""

from __future__ import annotations

from typing import Callable, Dict

import pandas as pd
import yfinance as yf

try:  # pragma: no cover - Streamlit not available during unit tests
    import streamlit as st
except Exception:  # pragma: no cover - fallback when Streamlit missing
    st = None  # type: ignore[assignment]

_TTL_BY_INTERVAL = {"1m": 60, "1h": 600, "1d": 3600, "1wk": 7200}
_DEFAULT_TTL = 3600
_CACHED_FETCHERS: Dict[int, Callable[..., pd.DataFrame]] = {}


def get_prices(ticker: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    """Download OHLCV data and normalise column names."""

    try:
        df = yf.download(
            ticker,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
    except Exception:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        # If multiple tickers accidentally passed, keep first level if present
        try:
            df = df.xs(ticker, axis=1, level=1)
        except Exception:
            df = df.droplevel(0, axis=1)

    df = df.rename(columns=str.lower)
    df.index = pd.to_datetime(df.index)
    return df.dropna()


def get_prices_cached(ticker: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    """Return cached prices with a TTL determined by the requested interval."""

    ttl = _TTL_BY_INTERVAL.get(interval, _DEFAULT_TTL)

    if st is None:
        return get_prices(ticker, start=start, end=end, interval=interval)

    fetcher = _CACHED_FETCHERS.get(ttl)
    if fetcher is None:
        fetcher = st.cache_data(show_spinner=False, ttl=ttl)(get_prices)
        _CACHED_FETCHERS[ttl] = fetcher

    return fetcher(ticker, start, end, interval)
