# pages/03_Backtest.py
"""Backtest — SMA crossover strategy."""

from __future__ import annotations
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quantboard.data import get_prices

# signal helper
try:
    from quantboard.backtest import sma_crossover_signals as make_signal
except Exception:
    try:
        from quantboard.strategies import signals_sma_crossover as make_signal  # legacy
    except Exception:
        make_signal = None

# backtest runner
try:
    from quantboard.backtest import run_backtest
except Exception:
    run_backtest = None

# optional SMA for overlays
try:
    from quantboard.indicators import sma
except Exception:
    sma = None

st.set_page_config(page_title="Backtest — SMA", page_icon="🧪", layout="wide")
st.title("Backtest — SMA crossover")

with st.sidebar:
    st.header("Parameters")
    ticker = st.text_input("Ticker", value="AAPL").strip().upper()
    fast = st.number_input("Fast SMA", min_value=2, max_value=200, value=20, step=1)
    slow = st.number_input("Slow SMA", min_value=5, max_value=400, value=50, step=1)
    interval = st.selectbox("Interval", ["1d", "1h", "1wk"], index=0)
    run_btn = st.button("Run", type="primary")

if not run_btn:
    st.info("Set parameters on the sidebar and press **Run**.")
    st.stop()

if fast >= slow:
    st.error("Fast SMA must be strictly less than Slow SMA.")
    st.stop()

with st.spinner("Downloading data..."):
    end = datetime.today().date()
    start = (datetime.today() - timedelta(days=365)).date()
    df = get_prices(ticker, start=start, end=end, interval=interval)

if df.empty or "close" not in df.columns:
    st.error("No data for the selected ticker/interval.")
    st.stop()

close = pd.to_numeric(df["close"], errors="coerce").dropna()
if close.empty:
    st.error("No valid closing prices to compute signals.")
    st.stop()

if make_signal is None:
    st.error("SMA crossover signal helper not found.")
    st.stop()

sig = make_signal(close, int(fast), int(slow))

if run_backtest is None:
    st.error("run_backtest() not found.")
    st.stop()

try:
    bt, metrics = run_backtest(close, sig)
except TypeError:
    try:
        bt, metrics = run_backtest(df, sig, fee_bps=0, slippage_bps=0, interval=interval)
    except Exception as e:
        st.exception(e)
        st.stop()

fig = go.Figure()
if {"open", "high", "low", "close"}.issubset(df.columns):
    fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"], name="OHLC"))
else:
    fig.add_trace(go.Scatter(x=close.index, y=close.values, mode="lines", name="Close"))

if sma is not None:
    fig.add_trace(go.Scatter(x=close.index, y=sma(close, int(fast))), name=f"SMA {fast}", mode="lines")
    fig.add_trace(go.Scatter(x=close.index, y=sma(close, int(slow))), name=f"SMA {slow}", mode="lines")

cross_up = sig.diff() == 1
cross_dn = sig.diff() == -1
fig.add_trace(go.Scatter(x=close.index[cross_up], y=close[cross_up], mode="markers",
                         marker_symbol="triangle-up", marker_size=9, name="Buy"))
fig.add_trace(go.Scatter(x=close.index[cross_dn], y=close[cross_dn], mode="markers",
                         marker_symbol="triangle-down", marker_size=9, name="Sell"))
fig.update_layout(margin=dict(l=40, r=20, t=40, b=40), height=520, title=f"{ticker} — SMA crossover")

col1, col2 = st.columns([2, 1])
with col1:
    st.plotly_chart(fig, use_container_width=True)
with col2:
    st.subheader("Metrics")
    mdf = pd.DataFrame([metrics]).T.rename(columns={0: "value"})
    try:
        st.dataframe(mdf.style.format("{:.4f}"), use_container_width=True)
    except Exception:
        st.dataframe(mdf, use_container_width=True)

st.subheader("Equity curve")
eq_fig = go.Figure(go.Scatter(x=bt.index, y=bt["equity"], mode="lines", name="Equity"))
eq_fig.update_layout(margin=dict(l=40, r=20, t=40, b=40), height=380)
st.plotly_chart(eq_fig, use_container_width=True)
