import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import streamlit as st

# Try to use the helper if it exists, but don't crash if not.
try:
    from quantboard.features.watchlist import load_watchlist  # type: ignore
except Exception:  # pragma: no cover - defensive import
    load_watchlist = None  # type: ignore


# ---------- Helpers ----------


def _read_watchlist() -> List[str]:
    """
    Return a list of tickers from data/watchlist.json.

    If quantboard.features.watchlist.load_watchlist exists, use it.
    Otherwise fall back to reading the JSON file directly.
    """
    if callable(load_watchlist):
        try:
            tickers = load_watchlist()
            if isinstance(tickers, dict):
                tickers = tickers.get("tickers", [])
            return [t.strip().upper() for t in tickers if t]
        except Exception:
            # Fallback to manual JSON read if helper fails.
            pass

    json_path = Path("data") / "watchlist.json"
    if not json_path.exists():
        return []

    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    if isinstance(data, dict):
        tickers = data.get("tickers", [])
    else:
        tickers = data

    return [str(t).strip().upper() for t in tickers if t]


def _rsi(series: pd.Series, length: int = 14) -> float:
    """Compute classic RSI for the last value in the series."""
    if len(series) < length + 1:
        return np.nan

    delta = series.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)

    avg_gain = gains.rolling(length).mean()
    avg_loss = losses.rolling(length).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return float(rsi.iloc[-1])


def _sma(series: pd.Series, window: int) -> float:
    if len(series) < window:
        return np.nan
    return float(series.rolling(window).mean().iloc[-1])


def _label_trend(
    rsi_value: float, sma20: float, sma50: float, close: float
) -> str:
    """
    Very simple Bullish/Bearish/Neutral label:
    - Bullish: close > sma20 > sma50 and RSI >= 55
    - Bearish: close < sma20 < sma50 and RSI <= 45
    - Otherwise: Neutral
    """
    if any(np.isnan(x) for x in [rsi_value, sma20, sma50, close]):
        return "Neutral"

    bullish = close > sma20 > sma50 and rsi_value >= 55
    bearish = close < sma20 < sma50 and rsi_value <= 45

    if bullish:
        return "Bullish"
    if bearish:
        return "Bearish"
    return "Neutral"


def _sma_crossover_state(sma20: float, sma50: float) -> str:
    """
    Return a simple crossover state for SMA(20) vs SMA(50).
    """
    if np.isnan(sma20) or np.isnan(sma50):
        return "N/A"
    if sma20 > sma50:
        return "Bullish (20 > 50)"
    if sma20 < sma50:
        return "Bearish (20 < 50)"
    return "Neutral (20 = 50)"


@st.cache_data(ttl=3600)
def _fetch_price_history(
    ticker: str, days: int = 90
) -> Optional[pd.DataFrame]:
    """
    Download ~last 60 trading days at 1d resolution.
    We use 90 calendar days to be safe and then trim.
    """
    try:
        import yfinance as yf  # Local import to keep py_compile tolerant
    except Exception:
        return None

    try:
        df = yf.download(ticker, period=f"{days}d", interval="1d", auto_adjust=False)
    except Exception:
        return None

    if df is None or df.empty:
        return None

    # Normalize OHLC column names to lower-case.
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )

    # Keep last ~60 trading days.
    df = df.tail(60)
    return df


def _compute_metrics_for_ticker(ticker: str) -> Dict[str, Any]:
    """
    Compute metrics for a single ticker.
    Robust to errors: on failure we return N/A row.
    """
    base_row: Dict[str, Any] = {
        "Ticker": ticker,
        "%1d": np.nan,
        "%5d": np.nan,
        "%30d": np.nan,
        "RSI(14)": np.nan,
        "Distance to SMA20 (%)": np.nan,
        "SMA20": np.nan,
        "SMA50": np.nan,
        "SMA20/50 State": "N/A",
        "Trend Label": "Neutral",
        "Open in Home": "",
    }

    try:
        df = _fetch_price_history(ticker)
        if df is None or df.empty or "close" not in df.columns:
            return base_row

        close = df["close"].dropna()
        if close.empty:
            return base_row

        last_close = float(close.iloc[-1])

        # Percentage returns.
        def pct_return(window: int) -> float:
            if len(close) <= window:
                return np.nan
            past = float(close.iloc[-(window + 1)])
            return (last_close / past - 1.0) * 100.0

        r1d = pct_return(1)
        r5d = pct_return(5)
        r30d = pct_return(30)

        sma20 = _sma(close, 20)
        sma50 = _sma(close, 50)

        dist_sma20 = (
            (last_close / sma20 - 1.0) * 100.0 if not np.isnan(sma20) else np.nan
        )

        rsi_val = _rsi(close, 14)
        state = _sma_crossover_state(sma20, sma50)
        label = _label_trend(rsi_val, sma20, sma50, last_close)

        row = {
            **base_row,
            "%1d": r1d,
            "%5d": r5d,
            "%30d": r30d,
            "RSI(14)": rsi_val,
            "Distance to SMA20 (%)": dist_sma20,
            "SMA20": sma20,
            "SMA50": sma50,
            "SMA20/50 State": state,
            "Trend Label": label,
            # Relative link that sets ?ticker=XYZ
            "Open in Home": f"?ticker={ticker}",
        }
        return row
    except Exception:
        # Any unexpected error → keep base_row with N/A values.
        return base_row


# ---------- Streamlit UI ----------


def main() -> None:
    st.set_page_config(page_title="Watchlist Screener", layout="wide")
    st.title("Watchlist Screener")

    tickers = _read_watchlist()

    if not tickers:
        st.info(
            "Your watchlist is empty. Add symbols to `data/watchlist.json` "
            "to see them here."
        )
        return

    st.caption(
        "Metrics computed from the last ~60 trading days at daily resolution."
    )

    progress = st.progress(0.0, text="Loading tickers...")
    rows: List[Dict[str, Any]] = []

    for idx, ticker in enumerate(tickers, start=1):
        rows.append(_compute_metrics_for_ticker(ticker))
        progress.progress(idx / len(tickers), text=f"Processed {ticker}")

    progress.empty()

    df = pd.DataFrame(rows)

    # Sort by %30d descending by default (if available).
    if "%30d" in df.columns:
        df = df.sort_values("%30d", ascending=False)

    st.subheader("Screener Table")

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Open in Home": st.column_config.LinkColumn(
                "Open in Home",
                display_text="Open",
                help="Open this ticker in the Home page (sets ?ticker=XYZ).",
            )
        },
    )

    st.caption(
        "Columns are sortable. Click on **Open in Home** to navigate with the "
        "selected ticker in the main page."
    )


if __name__ == "__main__":
    main()
