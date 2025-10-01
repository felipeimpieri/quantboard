"""Backtest page for the SMA crossover strategy."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quantboard.backtest import run_backtest
from quantboard.data import get_prices
from quantboard.indicators import sma
from quantboard.plots import apply_plotly_theme
from quantboard.ui.theme import apply_global_theme

try:
    from quantboard.strategies import signals_sma_crossover
except Exception:  # pragma: no cover - fallback when optional module is missing
    signals_sma_crossover = None  # type: ignore[assignment]

st.set_page_config(page_title="Backtest", page_icon="🧪", layout="wide")
apply_global_theme()


def _validate_prices(df: pd.DataFrame) -> pd.DataFrame | None:
    if df.empty or "close" not in df.columns:
        st.error("No data for the selected range/interval.")
        return None
    return df


def main() -> None:
    st.title("Backtest — SMA crossover")

    with st.sidebar:
        st.header("Parameters")
        ticker = st.text_input("Ticker", value="AAPL").strip().upper()
        end = st.date_input("To", value=date.today())
        start = st.date_input("From", value=date.today() - timedelta(days=365 * 2))
        interval = st.selectbox("Interval", ["1d", "1h", "1wk", "1m"], index=0)
        fast = st.number_input("Fast SMA", 5, 200, 20, step=1)
        slow = st.number_input("Slow SMA", 10, 400, 50, step=1)
        fee_bps = st.number_input("Fees (bps)", 0, 50, 0, step=1)
        slip_bps = st.number_input("Slippage (bps)", 0, 50, 0, step=1)
        run_btn = st.button("Run backtest", type="primary")

    st.info("Configure the sidebar parameters and run the backtest.")

    if not run_btn:
        return

    with st.spinner("Fetching data..."):
        df = get_prices(ticker, start=start, end=end, interval=interval)

    df = _validate_prices(df)
    if df is None:
        return

    # Series limpias
    close = pd.to_numeric(df["close"], errors="coerce")
    df = df.assign(close=close).dropna(subset=["close"])

    # Signals
    if signals_sma_crossover is not None:
        sig, _ = signals_sma_crossover(df["close"], fast=int(fast), slow=int(slow))
    else:
        # Local fallback if the shared strategies module is unavailable
        sma_fast = sma(df["close"], int(fast))
        sma_slow = sma(df["close"], int(slow))
        cross_up = (sma_fast > sma_slow) & (sma_fast.shift(1) <= sma_slow.shift(1))
        cross_dn = (sma_fast < sma_slow) & (sma_fast.shift(1) >= sma_slow.shift(1))
        sig = pd.Series(0, index=df.index, dtype=float)
        sig = sig.where(~cross_up, 1.0)
        sig = sig.where(~cross_dn, -1.0)
        sig = sig.replace(0, pd.NA).ffill().fillna(0.0)

    # Backtest
    bt, metrics = run_backtest(
        df,
        signals=sig,
        fee_bps=int(fee_bps),
        slippage_bps=int(slip_bps),
        interval=interval,
    )

    # --------- Charts ---------
    st.subheader("Price and SMAs")

    sma_fast = sma(df["close"], int(fast))
    sma_slow = sma(df["close"], int(slow))

    price_fig = go.Figure()
    price_fig.add_candlestick(
        x=df.index,
        open=pd.to_numeric(df.get("open", df["close"]), errors="coerce"),
        high=pd.to_numeric(df.get("high", df["close"]), errors="coerce"),
        low=pd.to_numeric(df.get("low", df["close"]), errors="coerce"),
        close=df["close"],
        name="OHLC",
    )
    price_fig.add_trace(
        go.Scatter(x=sma_fast.index, y=sma_fast, mode="lines", name=f"SMA {fast}")
    )
    price_fig.add_trace(
        go.Scatter(x=sma_slow.index, y=sma_slow, mode="lines", name=f"SMA {slow}")
    )

    # Buy/Sell markers
    changes = sig.diff().fillna(0)
    buys = df.index[changes > 0]
    sells = df.index[changes < 0]
    price_fig.add_trace(
        go.Scatter(
            x=buys,
            y=df.loc[buys, "close"],
            mode="markers",
            marker_symbol="triangle-up",
            marker_size=10,
            name="Buy",
        )
    )
    price_fig.add_trace(
        go.Scatter(
            x=sells,
            y=df.loc[sells, "close"],
            mode="markers",
            marker_symbol="triangle-down",
            marker_size=10,
            name="Sell",
        )
    )

    price_fig.update_layout(margin=dict(l=30, r=20, t=30, b=30), height=520)
    apply_plotly_theme(price_fig)
    st.plotly_chart(price_fig, use_container_width=True)

    st.subheader("Equity curve")
    eq_fig = go.Figure(go.Scatter(x=bt.index, y=bt["equity"], mode="lines", name="Equity"))
    eq_fig.update_layout(margin=dict(l=30, r=20, t=30, b=30), height=320)
    apply_plotly_theme(eq_fig)
    st.plotly_chart(eq_fig, use_container_width=True)

    # Metrics
    st.subheader("Metrics")
    mdf = pd.DataFrame([metrics]).T.rename(columns={0: "Value"})
    st.dataframe(mdf.style.format({"Value": "{:.4f}"}), use_container_width=True)


main()
