import pandas as pd
import yfinance as yf
try:
    import streamlit as st
    cache = st.cache_data(show_spinner=False, ttl=60)
except Exception:
    # fallback no-cache when not running in Streamlit
    def _no_cache(func):
        return func
    cache = _no_cache

@cache
def get_prices(ticker: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    try:
        df = yf.download(
            ticker,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
        if isinstance(df.columns, pd.MultiIndex):
            # If multiple tickers accidentally passed, keep first level if present
            try:
                df = df.xs(ticker, axis=1, level=1)
            except Exception:
                df = df.droplevel(0, axis=1)
        df = df.rename(columns=str.lower)
        df.index = pd.to_datetime(df.index)
        df = df.dropna()
        return df
    except Exception:
        return pd.DataFrame()
