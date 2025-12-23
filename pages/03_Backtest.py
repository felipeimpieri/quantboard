"""Backtest page for the SMA crossover strategy."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quantboard.backtest import run_backtest
from quantboard.data import get_prices_cached
from quantboard.indicators import sma
from quantboard.plots import apply_plotly_theme
from quantboard.ui.state import get_param, set_param, shareable_link_button
from quantboard.ui.theme import apply_global_theme

try:
    from quantboard.strategies import signals_sma_crossover
except Exception:  # pragma: no cover - optional dependency guard
    signals_sma_crossover = None  # type: ignore[assignment]

st.set_page_config(page_title="Backtest", page_icon="🧪", layout="wide")
apply_global_theme()


def _validate_prices(df: pd.DataFrame) -> pd.DataFrame | None:
    if df.empty or "close" not in df.columns:
        st.error("No data for the selected range/interval.")
        return None
    return df


def _clean_prices(df: pd.DataFrame) -> pd.DataFrame | None:
    price_cols = ["open", "high", "low", "close", "volume"]
    numeric = {col: pd.to_numeric(df.get(col), errors="coerce") for col in price_cols if col in df}
    clean = df.assign(**numeric).dropna(subset=["close"])
    if clean.empty:
        st.error("No price data available after cleaning.")
        return None
    return clean


def _run_signals(close: pd.Series, fast: int, slow: int) -> pd.Series:
    if signals_sma_crossover is not None:
        sig, _ = signals_sma_crossover(close, fast=fast, slow=slow)
        return sig

    sma_fast = sma(close, fast)
    sma_slow = sma(close, slow)
    cross_up = (sma_fast > sma_slow) & (sma_fast.shift(1) <= sma_slow.shift(1))
    cross_dn = (sma_fast < sma_slow) & (sma_fast.shift(1) >= sma_slow.shift(1))
    sig = pd.Series(0.0, index=close.index)
    sig = sig.where(~cross_up, 1.0)
    sig = sig.where(~cross_dn, -1.0)
    return sig.replace(0, pd.NA).ffill().fillna(0.0)


def main() -> None:
    st.title("Backtest — SMA crossover")

    shareable_link_button()

    today = date.today()
    default_start = today - timedelta(days=365 * 2)

    ticker = str(get_param("ticker", "AAPL")).strip().upper() or "AAPL"
    end = get_param("bt_end", today)
    start = get_param("bt_start", default_start)
    interval_options = ["1d", "1h", "1wk", "1m"]
    interval = str(get_param("interval", "1d"))
    if interval not in interval_options:
        interval = "1d"
    fast = int(get_param("fast", 20))
    slow = int(get_param("slow", 50))
    fee_bps = int(get_param("fee_bps", 0))
    slip_bps = int(get_param("slippage_bps", 0))

    fast = max(5, min(200, fast))
    slow = max(10, min(400, slow))
    fee_bps = max(0, min(50, fee_bps))
    slip_bps = max(0, min(50, slip_bps))

    with st.sidebar:
        st.header("Parameters")
        with st.form("backtest_form"):
            new_ticker = st.text_input("Ticker", value=ticker, key="bt_ticker_input").strip().upper()
            if new_ticker != ticker:
                set_param("ticker", new_ticker)
                ticker = new_ticker

            new_end = st.date_input("To", value=end, key="bt_end_input")
            if new_end != end:
                set_param("bt_end", new_end)
                end = new_end

            new_start = st.date_input("From", value=start, key="bt_start_input")
            if new_start != start:
                set_param("bt_start", new_start)
                start = new_start

            new_interval = st.selectbox(
                "Interval",
                interval_options,
                index=interval_options.index(interval),
                key="bt_interval_input",
            )
            if new_interval != interval:
                set_param("interval", new_interval)
                interval = new_interval

            new_fast = st.number_input("Fast SMA", 5, 200, int(fast), step=1, key="bt_fast_input")
            if int(new_fast) != int(fast):
                set_param("fast", int(new_fast))
                fast = int(new_fast)

            new_slow = st.number_input("Slow SMA", 10, 400, int(slow), step=1, key="bt_slow_input")
            if int(new_slow) != int(slow):
                set_param("slow", int(new_slow))
                slow = int(new_slow)

            new_fee = st.number_input("Fees (bps)", 0, 50, int(fee_bps), step=1, key="bt_fee_input")
            if int(new_fee) != int(fee_bps):
                set_param("fee_bps", int(new_fee))
                fee_bps = int(new_fee)

            new_slip = st.number_input(
                "Slippage (bps)", 0, 50, int(slip_bps), step=1, key="bt_slip_input"
            )
            if int(new_slip) != int(slip_bps):
                set_param("slippage_bps", int(new_slip))
                slip_bps = int(new_slip)
            submitted = st.form_submit_button("Run backtest", type="primary")

    st.info("Configure the sidebar parameters and run the backtest.")

    if not submitted:
        return

    if fast >= slow:
        st.error("Fast SMA must be smaller than Slow SMA.")
        return

    with st.spinner("Fetching data..."):
        df = get_prices_cached(ticker, start=start, end=end, interval=interval)

    df = _validate_prices(df)
    if df is None:
        return

    df = _clean_prices(df)
    if df is None:
        return

    signals = _run_signals(df["close"], fast=int(fast), slow=int(slow))

    bt, metrics = run_backtest(
        df,
        signals=signals,
        fee_bps=int(fee_bps),
        slippage_bps=int(slip_bps),
        interval=interval,
    )

    st.subheader("Price and SMAs")
    sma_fast = sma(df["close"], int(fast))
    sma_slow = sma(df["close"], int(slow))

    price_fig = go.Figure()
    price_fig.add_candlestick(
        x=df.index,
        open=df.get("open", df["close"]),
        high=df.get("high", df["close"]),
        low=df.get("low", df["close"]),
        close=df["close"],
        name="ohlc",
    )
    price_fig.add_trace(
        go.Scatter(x=sma_fast.index, y=sma_fast, mode="lines", name=f"SMA {int(fast)}"),
    )
    price_fig.add_trace(
        go.Scatter(x=sma_slow.index, y=sma_slow, mode="lines", name=f"SMA {int(slow)}"),
    )

    changes = signals.diff().fillna(0)
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
        ),
    )
    price_fig.add_trace(
        go.Scatter(
            x=sells,
            y=df.loc[sells, "close"],
            mode="markers",
            marker_symbol="triangle-down",
            marker_size=10,
            name="Sell",
        ),
    )

    price_fig.update_layout(margin=dict(l=30, r=20, t=30, b=30), height=520)
    apply_plotly_theme(price_fig)
    st.plotly_chart(price_fig, use_container_width=True)

    st.subheader("Equity curve")
    eq_fig = go.Figure(go.Scatter(x=bt.index, y=bt["equity"], mode="lines", name="Equity"))
    eq_fig.update_layout(margin=dict(l=30, r=20, t=30, b=30), height=320)
    apply_plotly_theme(eq_fig)
    st.plotly_chart(eq_fig, use_container_width=True)

    st.subheader("Metrics")
    metrics_order = [
        "CAGR",
        "Sharpe",
        "Sortino",
        "Max Drawdown",
        "Win rate",
        "Avg trade return",
        "Exposure (%)",
        "Trades count",
    ]
    percent_metrics = {
        "CAGR",
        "Max Drawdown",
        "Win rate",
        "Avg trade return",
        "Exposure (%)",
    }
    ratio_metrics = {"Sharpe", "Sortino"}

    metrics_rows = []
    for key in metrics_order:
        value = metrics.get(key, 0.0)
        if key == "Trades count":
            display = f"{int(value)}"
        elif key in percent_metrics:
            display = f"{value:.2%}"
        elif key in ratio_metrics:
            display = f"{value:.2f}"
        else:
            display = f"{value:.4f}"
        metrics_rows.append({"Metric": key, "Value": display})

    metrics_df = pd.DataFrame(metrics_rows).set_index("Metric")
    st.dataframe(metrics_df, use_container_width=True)


main()
