"""Alerts page scanning watchlist tickers for technical signals."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
import streamlit as st

from quantboard.data import get_prices
from quantboard.features.watchlist import load_watchlist
from quantboard.indicators import rsi, sma
from quantboard.ui.theme import apply_global_theme

st.set_page_config(page_title="Alerts", page_icon="🚨", layout="wide")
apply_global_theme()

st.title("Alerts")
st.caption("Scan saved tickers for recent technical events over the last 90 trading days.")

watchlist: List[str] = load_watchlist()
if not watchlist:
    st.info("Your watchlist is empty. Add tickers from the Watchlist page.")
    st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def load_daily_history(ticker: str) -> pd.DataFrame:
    """Fetch up to the last 90 trading days of daily data for a ticker."""
    end = datetime.utcnow().date()
    start = end - timedelta(days=200)
    df = get_prices(ticker, start=start.isoformat(), end=end.isoformat(), interval="1d")
    if df.empty:
        return df
    if len(df) > 90:
        df = df.tail(90)
    return df


def format_price(value: float | None) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def format_extra(parts: Dict[str, float | None]) -> str:
    formatted = []
    for key, val in parts.items():
        if val is None or pd.isna(val):
            continue
        formatted.append(f"{key}={val:.2f}")
    return ", ".join(formatted) if formatted else ""


scan_col1, scan_col2, scan_col3 = st.columns(3)
with scan_col1:
    scan_sma_cross = st.checkbox("SMA crossover (20/50)", value=True)
with scan_col2:
    scan_rsi_extremes = st.checkbox("RSI overbought/oversold (70/30)", value=True)
with scan_col3:
    scan_donchian = st.checkbox("Donchian breakout (20)", value=True)

controls = st.columns([1, 1])
with controls[0]:
    rescan_clicked = st.button("Re-scan", type="primary")
with controls[1]:
    st.write("")

if rescan_clicked:
    load_daily_history.clear()

if not any([scan_sma_cross, scan_rsi_extremes, scan_donchian]):
    st.info("Enable at least one signal to run the scan.")
    st.stop()

results: List[Dict[str, object]] = []
failed: List[str] = []

with st.spinner("Scanning alerts..."):
    for ticker in watchlist:
        try:
            df = load_daily_history(ticker)
        except Exception:
            df = pd.DataFrame()
        if df.empty or "close" not in df.columns:
            failed.append(ticker)
            continue

        df = df.sort_index()
        close = pd.to_numeric(df["close"], errors="coerce")
        close = close.dropna()
        if close.empty:
            failed.append(ticker)
            continue

        prices = pd.DataFrame({"close": close})
        if "high" in df.columns:
            prices["high"] = pd.to_numeric(df["high"], errors="coerce").reindex(prices.index)
        else:
            prices["high"] = prices["close"]
        if "low" in df.columns:
            prices["low"] = pd.to_numeric(df["low"], errors="coerce").reindex(prices.index)
        else:
            prices["low"] = prices["close"]
        prices = prices.fillna(method="ffill").dropna()

        if prices.empty or len(prices) < 5:
            failed.append(ticker)
            continue

        if scan_sma_cross:
            sma_fast = sma(prices["close"], 20)
            sma_slow = sma(prices["close"], 50)
            diff = sma_fast - sma_slow
            diff_prev = diff.shift(1)
            crosses_up = (diff > 0) & (diff_prev <= 0)
            crosses_down = (diff < 0) & (diff_prev >= 0)
            for timestamp, is_cross in crosses_up.items():
                if is_cross and not pd.isna(diff_prev.loc[timestamp]):
                    results.append(
                        {
                            "Ticker": ticker,
                            "Date": timestamp.date().isoformat(),
                            "Signal": "SMA 20/50 bullish cross",
                            "Price": format_price(prices["close"].loc[timestamp]),
                            "Extra": format_extra(
                                {
                                    "SMA20": sma_fast.loc[timestamp],
                                    "SMA50": sma_slow.loc[timestamp],
                                }
                            ),
                        }
                    )
            for timestamp, is_cross in crosses_down.items():
                if is_cross and not pd.isna(diff_prev.loc[timestamp]):
                    results.append(
                        {
                            "Ticker": ticker,
                            "Date": timestamp.date().isoformat(),
                            "Signal": "SMA 20/50 bearish cross",
                            "Price": format_price(prices["close"].loc[timestamp]),
                            "Extra": format_extra(
                                {
                                    "SMA20": sma_fast.loc[timestamp],
                                    "SMA50": sma_slow.loc[timestamp],
                                }
                            ),
                        }
                    )

        if scan_rsi_extremes:
            rsi_series = rsi(prices["close"], period=14)
            rsi_prev = rsi_series.shift(1)
            overbought = (rsi_series >= 70) & (rsi_prev < 70)
            oversold = (rsi_series <= 30) & (rsi_prev > 30)
            for timestamp, triggered in overbought.items():
                if triggered and not pd.isna(rsi_prev.loc[timestamp]):
                    results.append(
                        {
                            "Ticker": ticker,
                            "Date": timestamp.date().isoformat(),
                            "Signal": "RSI overbought",
                            "Price": format_price(prices["close"].loc[timestamp]),
                            "Extra": format_extra({"RSI": rsi_series.loc[timestamp]}),
                        }
                    )
            for timestamp, triggered in oversold.items():
                if triggered and not pd.isna(rsi_prev.loc[timestamp]):
                    results.append(
                        {
                            "Ticker": ticker,
                            "Date": timestamp.date().isoformat(),
                            "Signal": "RSI oversold",
                            "Price": format_price(prices["close"].loc[timestamp]),
                            "Extra": format_extra({"RSI": rsi_series.loc[timestamp]}),
                        }
                    )

        if scan_donchian:
            window = 20
            high_series = prices["high"]
            low_series = prices["low"]
            upper_band = high_series.rolling(window).max().shift(1)
            lower_band = low_series.rolling(window).min().shift(1)
            breakout_up = (prices["close"] > upper_band) & upper_band.notna()
            breakout_down = (prices["close"] < lower_band) & lower_band.notna()
            for timestamp, triggered in breakout_up.items():
                if triggered:
                    results.append(
                        {
                            "Ticker": ticker,
                            "Date": timestamp.date().isoformat(),
                            "Signal": "Donchian breakout up",
                            "Price": format_price(prices["close"].loc[timestamp]),
                            "Extra": format_extra({"Upper": upper_band.loc[timestamp]}),
                        }
                    )
            for timestamp, triggered in breakout_down.items():
                if triggered:
                    results.append(
                        {
                            "Ticker": ticker,
                            "Date": timestamp.date().isoformat(),
                            "Signal": "Donchian breakout down",
                            "Price": format_price(prices["close"].loc[timestamp]),
                            "Extra": format_extra({"Lower": lower_band.loc[timestamp]}),
                        }
                    )

if not results and failed:
    st.error("No data for selected range/interval.")
    st.stop()

if results:
    alerts_df = pd.DataFrame(results)
    alerts_df = alerts_df.sort_values(["Date", "Ticker", "Signal"], ascending=[False, True, True]).reset_index(drop=True)

    csv_bytes = alerts_df.to_csv(index=False).encode("utf-8")

    st.subheader("Alerts")
    st.download_button(
        "Copy CSV",
        data=csv_bytes,
        file_name="alerts.csv",
        mime="text/csv",
        help="Download the current alerts as a CSV file.",
    )

    st.data_editor(
        alerts_df,
        hide_index=True,
        use_container_width=True,
        disabled=True,
        column_config={
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Date": st.column_config.TextColumn("Date"),
            "Signal": st.column_config.TextColumn("Signal"),
            "Extra": st.column_config.TextColumn("Extra"),
        },
    )
else:
    st.info("No alerts were triggered for the selected signals.")

if failed:
    st.warning(
        "Data unavailable for: " + ", ".join(sorted(set(failed))) + ".",
        icon="⚠️",
    )
