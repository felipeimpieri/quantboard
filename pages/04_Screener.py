"""Screener page displaying technical metrics for the saved watchlist."""
from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Dict, List

import numpy as np
import pandas as pd
import streamlit as st

from quantboard.data import get_prices
from quantboard.features.watchlist import load_watchlist
from quantboard.indicators import rsi, sma
from quantboard.ui.theme import apply_global_theme

st.set_page_config(page_title="Screener", page_icon="🧮", layout="wide")
apply_global_theme()

st.title("Screener")

watchlist: List[str] = load_watchlist()
if not watchlist:
    st.info("Your watchlist is empty. Add tickers from the Watchlist page.")
    st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def load_daily_history(ticker: str) -> pd.DataFrame:
    """Fetch up to the last 60 trading days of daily data for a ticker."""
    end = datetime.utcnow().date()
    start = end - timedelta(days=120)
    df = get_prices(ticker, start=start.isoformat(), end=end.isoformat(), interval="1d")
    if df.empty:
        return df
    if len(df) > 60:
        df = df.tail(60)
    return df


def pct_change(series: pd.Series, periods: int) -> float | None:
    if len(series) <= periods:
        return None
    change = series.pct_change(periods=periods).iloc[-1]
    if pd.isna(change) or not np.isfinite(change):
        return None
    return float(change * 100.0)


def compute_row(ticker: str, data: pd.DataFrame) -> Dict[str, object]:
    close = pd.to_numeric(data.get("close"), errors="coerce").dropna()
    row: Dict[str, object] = {
        "Ticker": ticker,
        "Last price": math.nan,
        "%1d": math.nan,
        "%5d": math.nan,
        "%30d": math.nan,
        "RSI(14)": math.nan,
        "distance_to_SMA20 (%)": math.nan,
        "Fast/Slow crossover": "N/A",
        "Signal": "N/A",
        "Open in Home": f"streamlit_app.py?ticker={ticker}",
    }

    if close.empty:
        return row

    last_price = float(close.iloc[-1])
    row["Last price"] = last_price

    for periods, key in [(1, "%1d"), (5, "%5d"), (30, "%30d")]:
        pct_val = pct_change(close, periods)
        if pct_val is not None:
            row[key] = pct_val

    rsi_series = rsi(close, period=14).dropna()
    if not rsi_series.empty:
        row["RSI(14)"] = float(rsi_series.iloc[-1])

    sma_fast = sma(close, 20)
    sma_slow = sma(close, 50)
    sma20_val = sma_fast.iloc[-1]
    sma50_val = sma_slow.iloc[-1]
    sma20_last = float(sma20_val) if pd.notna(sma20_val) else math.nan
    sma50_last = float(sma50_val) if pd.notna(sma50_val) else math.nan

    if not math.isnan(sma20_last):
        row["distance_to_SMA20 (%)"] = ((last_price - sma20_last) / sma20_last) * 100.0 if sma20_last else math.nan

    state = "N/A"
    if not math.isnan(sma20_last) and not math.isnan(sma50_last):
        if sma20_last > sma50_last:
            state = "Bullish"
        elif sma20_last < sma50_last:
            state = "Bearish"
        else:
            state = "Neutral"
    row["Fast/Slow crossover"] = state

    signal = "Neutral"
    rsi_value = row.get("RSI(14)")
    if isinstance(rsi_value, float):
        if state == "Bullish" and rsi_value >= 55:
            signal = "Bullish"
        elif state == "Bearish" and rsi_value <= 45:
            signal = "Bearish"
    row["Signal"] = signal if state != "N/A" else "N/A"

    return row


rows: List[Dict[str, object]] = []
failed: List[str] = []

with st.spinner("Loading market data..."):
    for ticker in watchlist:
        try:
            df = load_daily_history(ticker)
        except Exception:
            df = pd.DataFrame()
        if df.empty or "close" not in df.columns:
            failed.append(ticker)
            rows.append(
                {
                    "Ticker": ticker,
                    "Last price": math.nan,
                    "%1d": math.nan,
                    "%5d": math.nan,
                    "%30d": math.nan,
                    "RSI(14)": math.nan,
                    "distance_to_SMA20 (%)": math.nan,
                    "Fast/Slow crossover": "N/A",
                    "Signal": "N/A",
                    "Open in Home": f"streamlit_app.py?ticker={ticker}",
                }
            )
            continue
        rows.append(compute_row(ticker, df))

if not rows:
    st.error("No data for selected range/interval.")
    st.stop()

metrics_df = pd.DataFrame(rows)

number_columns = {
    "Last price": st.column_config.NumberColumn("Last price", format="$%.2f"),
    "%1d": st.column_config.NumberColumn("%1d", format="%.2f%%"),
    "%5d": st.column_config.NumberColumn("%5d", format="%.2f%%"),
    "%30d": st.column_config.NumberColumn("%30d", format="%.2f%%"),
    "RSI(14)": st.column_config.NumberColumn("RSI(14)", format="%.2f"),
    "distance_to_SMA20 (%)": st.column_config.NumberColumn("distance_to_SMA20 (%)", format="%.2f%%"),
}

st.data_editor(
    metrics_df,
    hide_index=True,
    use_container_width=True,
    disabled=True,
    column_config={
        **number_columns,
        "Fast/Slow crossover": st.column_config.TextColumn("Fast/Slow crossover"),
        "Signal": st.column_config.TextColumn("Signal"),
        "Open in Home": st.column_config.LinkColumn(
            "Open in Home",
            display_text="Open",
            help="Open this ticker on the Home page",
        ),
    },
)

if failed:
    st.warning(
        "Data unavailable for: " + ", ".join(sorted(set(failed))) + ".",
        icon="⚠️",
    )

st.caption("Daily metrics based on the last 60 trading sessions.")
