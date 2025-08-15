import streamlit as st
import pandas as pd
from datetime import date, timedelta
from plotly import graph_objs as go

# QuantBoard package
from quantboard.data import get_prices
from quantboard.indicators import sma, ema, rsi, macd, bollinger
from quantboard.strategies import (
    signals_sma_crossover,
    signals_rsi,
    signals_bollinger_mean_reversion,
    signals_donchian_breakout,
)
from quantboard.backtest import run_backtest
from quantboard.plots import price_chart, heatmap_metric
from quantboard.optimize import grid_search_sma

st.set_page_config(page_title="QuantBoard v0.2", page_icon="📈", layout="wide")

# --- Sidebar ---
st.sidebar.header("Configuración")

ticker = st.sidebar.text_input("Ticker", value="AAPL")
end = st.sidebar.date_input("Hasta", value=date.today())
start = st.sidebar.date_input("Desde", value=date.today() - timedelta(days=365))
interval = st.sidebar.selectbox("Intervalo", options=["1d", "1wk", "1mo"], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("Indicadores")
use_sma = st.sidebar.checkbox("SMA", value=True)
sma_fast = st.sidebar.number_input("SMA rápida", min_value=2, max_value=200, value=20)
sma_slow = st.sidebar.number_input("SMA lenta", min_value=5, max_value=400, value=50)

use_ema = st.sidebar.checkbox("EMA", value=False)
ema_len = st.sidebar.number_input("EMA período", min_value=2, max_value=200, value=20)

use_rsi = st.sidebar.checkbox("RSI", value=False)
rsi_len = st.sidebar.number_input("RSI período", min_value=2, max_value=50, value=14)

use_bb = st.sidebar.checkbox("Bollinger", value=False)
bb_len = st.sidebar.number_input("BB ventana", min_value=5, max_value=200, value=20)
bb_std = st.sidebar.number_input("BB desv std", min_value=1.0, max_value=4.0, value=2.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("Estrategia")
strategy = st.sidebar.selectbox(
    "Señales",
    ["SMA crossover", "RSI thresholds", "Bollinger mean reversion", "Donchian breakout"],
)
fee_bps = st.sidebar.number_input("Comisión (bps)", min_value=0, max_value=50, value=0)
slip_bps = st.sidebar.number_input("Slippage (bps)", min_value=0, max_value=50, value=0)

run_btn = st.sidebar.button("Ejecutar", type="primary")

st.sidebar.markdown("---")
st.sidebar.subheader("Optimización (SMA)")
fast_min, fast_max = st.sidebar.slider("Rango SMA rápida", 5, 50, (10, 20))
slow_min, slow_max = st.sidebar.slider("Rango SMA lenta", 20, 200, (50, 100))
opt_btn = st.sidebar.button("Optimizar grid")

st.title("QuantBoard — Análisis técnico y Backtesting")
st.info("Configurá a la izquierda y apretá **Ejecutar** para empezar.")

# --- Main run ---
if run_btn:
    with st.spinner("Descargando datos..."):
        df = get_prices(ticker, start=start, end=end, interval=interval)
        df = df.dropna()

    overlays = {}

    # Señales según estrategia
    if strategy == "SMA crossover":
        sig, extra = signals_sma_crossover(df["Close"], fast=int(sma_fast), slow=int(sma_slow))
        overlays.update(extra)
    elif strategy == "RSI thresholds":
        sig, extra = signals_rsi(df["Close"], period=int(rsi_len), lower=30, upper=70)
        overlays.update(extra)
    elif strategy == "Bollinger mean reversion":
        sig, extra = signals_bollinger_mean_reversion(df["Close"], window=int(bb_len), n_std=float(bb_std))
        overlays.update(extra)
    else:  # Donchian
        sig, extra = signals_donchian_breakout(df["High"], df["Low"], df["Close"], window=int(bb_len))
        overlays.update(extra)

    # Overlays visuales según checkboxes
    if use_sma:
        overlays.setdefault("SMA_fast", sma(df["Close"], int(sma_fast)))
        overlays.setdefault("SMA_slow", sma(df["Close"], int(sma_slow)))
    if use_ema:
        overlays["EMA"] = ema(df["Close"], int(ema_len))
    if use_bb:
        overlays["BB"] = bollinger(df["Close"], int(bb_len), float(bb_std))
    if use_rsi and "RSI" not in overlays:
        overlays["RSI"] = rsi(df["Close"], int(rsi_len))

    # Backtest
    bt, metrics = run_backtest(df, sig, fee_bps=int(fee_bps), slippage_bps=int(slip_bps), interval=interval)

    # Chart
    fig = price_chart(df, overlays)
    st.plotly_chart(fig, use_container_width=True)

    # Métricas
    mdf = pd.DataFrame([metrics]).T.rename(columns={0: "value"})
    st.subheader("Métricas")
    st.dataframe(mdf.style.format({"value": "{:.4f}"}))

    # Equity
    eq_fig = go.Figure(go.Scatter(x=bt.index, y=bt["equity"], mode="lines", name="Equity"))
    eq_fig.update_layout(title="Curva de equity")
    st.plotly_chart(eq_fig, use_container_width=True)

# --- Optimization grid ---
if opt_btn:
    with st.spinner("Buscando parámetros (SMA grid)..."):
        df = get_prices(ticker, start=start, end=end, interval=interval)
        z = grid_search_sma(
            df["Close"],
            fast_range=range(int(fast_min), int(fast_max) + 1),
            slow_range=range(int(slow_min), int(slow_max) + 1),
            fee_bps=int(fee_bps),
            slippage_bps=int(slip_bps),
            interval=interval,
            metric="Sharpe",
        )
    st.subheader("SMA grid (Sharpe)")
    st.plotly_chart(heatmap_metric(z, title="SMA grid – Sharpe"), use_container_width=True)