"""Watchlist screener with basic momentum and trend signals."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

import pandas as pd
import streamlit as st

from quantboard.data import get_prices_cached
from quantboard.features.watchlist import load_watchlist
from quantboard.indicators import rsi, sma
from quantboard.ui.state import set_param, shareable_link_button
from quantboard.ui.theme import apply_global_theme

st.set_page_config(page_title="Screener", page_icon="🧭", layout="wide")
apply_global_theme()

st.title("Screener")
shareable_link_button()


def _pct_change(close: pd.Series, days: int) -> float | None:
    if len(close) <= days:
        return None
    base = float(close.iloc[-(days + 1)])
    last = float(close.iloc[-1])
    if base == 0:
        return None
    return (last / base) - 1.0


def _distance(current: float, anchor: float | None) -> float | None:
    if anchor is None or anchor == 0:
        return None
    return (current / anchor) - 1.0


@st.cache_data(ttl=3600, show_spinner=False)
def load_screener_data(tickers: Iterable[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    start = (datetime.today() - timedelta(days=90)).date()
    end = datetime.today().date()

    for ticker in tickers:
        try:
            df = get_prices_cached(ticker, start=start, end=end, interval="1d")
        except Exception:
            df = pd.DataFrame()

        if df.empty or "close" not in df.columns:
            rows.append({"ticker": ticker, "error": True})
            continue

        close = pd.to_numeric(df["close"], errors="coerce").dropna()
        if close.empty:
            rows.append({"ticker": ticker, "error": True})
            continue

        last_price = float(close.iloc[-1])
        pct_1d = _pct_change(close, 1)
        pct_5d = _pct_change(close, 5)
        pct_30d = _pct_change(close, 30)

        sma_20 = sma(close, 20).iloc[-1]
        sma_50 = sma(close, 50).iloc[-1]
        dist_sma20 = _distance(last_price, float(sma_20) if pd.notna(sma_20) else None)
        rsi_14 = rsi(close, period=14).iloc[-1]

        sma_state = "N/A"
        if pd.notna(sma_20) and pd.notna(sma_50):
            sma_state = "20 > 50" if sma_20 > sma_50 else "20 < 50"

        label = "Neutral"
        if pd.notna(sma_20) and pd.notna(sma_50) and pd.notna(rsi_14):
            if sma_20 > sma_50 and rsi_14 >= 55:
                label = "Bullish"
            elif sma_20 < sma_50 and rsi_14 <= 45:
                label = "Bearish"

        rows.append(
            {
                "ticker": ticker,
                "last": last_price,
                "pct_1d": pct_1d,
                "pct_5d": pct_5d,
                "pct_30d": pct_30d,
                "rsi_14": float(rsi_14) if pd.notna(rsi_14) else None,
                "dist_sma20": dist_sma20,
                "sma_state": sma_state,
                "label": label,
                "error": False,
            }
        )

    return pd.DataFrame(rows)


def _fmt_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value * 100.0:.2f}%"


def _fmt_float(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.2f}"


def _open_home(ticker: str) -> None:
    set_param("ticker", ticker)
    try:
        st.switch_page("streamlit_app.py")
    except Exception:  # pragma: no cover - runtime dependent
        st.info("Open Home from the menu; the ticker was set.")


def main() -> None:
    tickers = load_watchlist()
    if not tickers:
        st.info("Add tickers to your watchlist to see the screener.")
        return

    with st.spinner("Loading screener data..."):
        df = load_screener_data(tickers)

    if df.empty:
        st.warning("No data available for the current watchlist.")
        return

    sort_options = {
        "Ticker": "ticker",
        "1d %": "pct_1d",
        "5d %": "pct_5d",
        "30d %": "pct_30d",
        "RSI(14)": "rsi_14",
        "Distance to SMA20 %": "dist_sma20",
    }
    col_sort, col_order = st.columns([2, 1])
    selected_sort = col_sort.selectbox("Sort by", list(sort_options.keys()), index=1)
    descending = col_order.toggle("Descending", value=True)

    sort_key = sort_options[selected_sort]
    df_sorted = df.sort_values(by=sort_key, ascending=not descending, na_position="last")

    header_cols = st.columns([1.2, 1.2, 1.2, 1.2, 1.2, 1.4, 1.2, 1.2, 1.4])
    headers = [
        "**Ticker**",
        "**1d %**",
        "**5d %**",
        "**30d %**",
        "**RSI(14)**",
        "**Distance to SMA20 %**",
        "**SMA 20/50**",
        "**Label**",
        "**Action**",
    ]
    for col, label in zip(header_cols, headers):
        col.markdown(label)

    for idx, row in df_sorted.iterrows():
        cols = st.columns([1.2, 1.2, 1.2, 1.2, 1.2, 1.4, 1.2, 1.2, 1.4])
        cols[0].write(str(row.get("ticker", "")))

        if row.get("error"):
            cols[1].write("N/A")
            cols[2].write("N/A")
            cols[3].write("N/A")
            cols[4].write("N/A")
            cols[5].write("N/A")
            cols[6].write("N/A")
            cols[7].write("N/A")
        else:
            cols[1].write(_fmt_pct(row.get("pct_1d")))
            cols[2].write(_fmt_pct(row.get("pct_5d")))
            cols[3].write(_fmt_pct(row.get("pct_30d")))
            cols[4].write(_fmt_float(row.get("rsi_14")))
            cols[5].write(_fmt_pct(row.get("dist_sma20")))
            cols[6].write(row.get("sma_state", "N/A"))
            cols[7].write(row.get("label", ""))

        if cols[8].button("Open in Home", key=f"open_{row.get('ticker','')}_{idx}"):
            _open_home(str(row.get("ticker", "")))


if __name__ == "__main__":
    main()
