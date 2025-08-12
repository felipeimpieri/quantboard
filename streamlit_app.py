import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from datetime import date, timedelta

from quantboard.data import get_prices
from quantboard.indicators import sma, ema, rsi, macd
from quantboard.strategies import signals_sma_crossover, signals_rsi
from quantboard.backtest import run_backtest
from quantboard.plots import price_chart

st.set_page_config(page_title="QuantBoard", page_icon="📈", layout="wide")

st.title("📈 QuantBoard — Análisis técnico y Backtesting")
st.caption("Streamlit + yfinance + Plotly. Hecho para mostrar skills en GitHub.")

with st.sidebar:
    st.header("Configuración")
    ticker = st.text_input("Ticker", value="AAPL").upper().strip()
    end = st.date_input("Hasta", value=date.today())
    start = st.date_input("Desde", value=date.today() - timedelta(days=365))
    interval = st.selectbox("Intervalo", ["1d", "1h", "1wk"], index=0)

    st.subheader("Indicadores")
    show_sma = st.checkbox("SMA", value=True)
    sma_fast = st.number_input("SMA rápida", min_value=2, max_value=200, value=20, step=1)
    sma_slow = st.number_input("SMA lenta", min_value=2, max_value=400, value=50, step=1)

    show_rsi = st.checkbox("RSI", value=True)
    rsi_len = st.number_input("RSI período", min_value=2, max_value=100, value=14, step=1)

    show_macd = st.checkbox("MACD", value=False)

    st.subheader("Estrategia")
    strat = st.selectbox("Estrategia", ["sma_crossover", "rsi"])
    fee_bps = st.number_input("Fee por trade (bps)", min_value=0, max_value=100, value=5, step=1)
    slippage_bps = st.number_input("Slippage (bps)", min_value=0, max_value=100, value=2, step=1)

    run = st.button("▶️ Ejecutar")

if run:
    if not ticker:
        st.error("Ingresá un ticker (ej: AAPL, MSFT, TSLA).")
        st.stop()

    with st.spinner("Descargando datos..."):
        df = get_prices(ticker, start=str(start), end=str(end), interval=interval)
        if df is None or df.empty:
            st.error("No se pudieron traer datos. Probá otro ticker/intervalo.")
            st.stop()

    # Indicadores
    if show_sma:
        df[f"SMA_{int(sma_fast)}"] = sma(df["Close"], int(sma_fast))
        df[f"SMA_{int(sma_slow)}"] = sma(df["Close"], int(sma_slow))
    if show_rsi:
        df["RSI"] = rsi(df["Close"], int(rsi_len))
    if show_macd:
        macd_df = macd(df["Close"])
        df = pd.concat([df, macd_df], axis=1)

    # Señales
    if strat == "sma_crossover":
        sig = signals_sma_crossover(df["Close"], fast=int(sma_fast), slow=int(sma_slow))
    else:
        sig = signals_rsi(df["Close"], length=int(rsi_len), low=30, high=70)

    # Backtest
    bt = run_backtest(df, sig, fee_bps=int(fee_bps), slippage_bps=int(slippage_bps), interval=interval)

    # Layout
    t1, t2 = st.tabs(["📊 Precio e Indicadores", "🧪 Backtest"])

    with t1:
        fig = price_chart(df, show_sma=show_sma, sma_fast=int(sma_fast), sma_slow=int(sma_slow))
        st.plotly_chart(fig, use_container_width=True)

        if show_rsi:
            rsi_fig = go.Figure()
            rsi_fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], mode="lines", name="RSI"))
            rsi_fig.add_hline(y=30, line_dash="dot")
            rsi_fig.add_hline(y=70, line_dash="dot")
            rsi_fig.update_layout(height=250, margin=dict(l=10,r=10,t=30,b=10))
            st.subheader("RSI")
            st.plotly_chart(rsi_fig, use_container_width=True)

    with t2:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Return", f"{bt['metrics']['total_return']:.2%}")
        c2.metric("CAGR", f"{bt['metrics']['cagr']:.2%}")
        c3.metric("Max Drawdown", f"{bt['metrics']['max_drawdown']:.2%}")
        c4.metric("Sharpe", f"{bt['metrics']['sharpe']:.2f}")

        eq_fig = go.Figure()
        eq_fig.add_trace(go.Scatter(x=bt["equity"].index, y=bt["equity"].values, mode="lines", name="Equity"))
        eq_fig.update_layout(title="Equity Curve", height=350, margin=dict(l=10,r=10,t=30,b=10))
        st.plotly_chart(eq_fig, use_container_width=True)

        st.subheader("Trades")
        st.dataframe(bt["trades"])

        st.download_button("Descargar resultados (CSV)",
                           data=bt["results_csv"].encode("utf-8"),
                           file_name=f"{ticker}_{strat}_results.csv",
                           mime="text/csv")

else:
    st.info("Configurá la izquierda y apretá **Ejecutar** para empezar.")
