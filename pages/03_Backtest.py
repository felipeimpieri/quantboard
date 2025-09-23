"""Página de backtest para estrategia SMA crossover."""

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quantboard.data import get_prices
from quantboard.strategies import signals_sma_crossover
from quantboard.backtest import run_backtest


st.set_page_config(page_title="Backtest SMA", page_icon="🧪", layout="wide")

st.title("Backtest SMA crossover")
st.info("Ingresá los parámetros en la barra lateral y ejecutá el backtest.")

st.sidebar.header("Parámetros")
ticker = st.sidebar.text_input("Ticker", value="AAPL")
start_default = date.today() - timedelta(days=365)
start = st.sidebar.date_input("Desde", value=start_default)
end = st.sidebar.date_input("Hasta", value=date.today())
fast = st.sidebar.number_input("SMA rápida", min_value=2, max_value=200, value=20)
slow = st.sidebar.number_input("SMA lenta", min_value=5, max_value=400, value=50)
run_btn = st.sidebar.button("Correr backtest", type="primary")

if run_btn:
    if not ticker:
        st.error("Ingresá un ticker válido.")
    elif start >= end:
        st.error("La fecha 'Desde' debe ser anterior a 'Hasta'.")
    elif fast >= slow:
        st.error("La SMA rápida debe ser menor que la SMA lenta.")
    else:
        df = pd.DataFrame()
        sig = None
        overlays: dict[str, pd.Series] = {}
        bt = None
        metrics: dict[str, float] = {}

        with st.spinner("Descargando datos y ejecutando backtest..."):
            df = get_prices(ticker, start=start, end=end, interval="1d")
            if not df.empty and not df["Close"].dropna().empty:
                sig, overlays = signals_sma_crossover(
                    df["Close"], fast=int(fast), slow=int(slow)
                )
                bt, metrics = run_backtest(df, sig, interval="1d")

        if (
            df.empty
            or df["Close"].dropna().empty
            or sig is None
            or bt is None
            or not metrics
        ):
            st.error("No se pudieron obtener datos para el ticker y rango seleccionados.")
        else:
            st.subheader("Precio y señales")
            fig = go.Figure(
                data=[
                    go.Candlestick(
                        x=df.index,
                        open=df["Open"],
                        high=df["High"],
                        low=df["Low"],
                        close=df["Close"],
                        name="Precio",
                    )
                ]
            )

            for name in ("SMA_fast", "SMA_slow"):
                series = overlays.get(name)
                if series is not None and not series.dropna().empty:
                    fig.add_trace(
                        go.Scatter(
                            x=series.index,
                            y=series.values,
                            mode="lines",
                            name=name,
                        )
                    )

            signal_change = sig.diff().fillna(0)
            buys = signal_change > 0
            sells = signal_change < 0

            buy_idx = buys[buys].index
            sell_idx = sells[sells].index

            if not buy_idx.empty:
                fig.add_trace(
                    go.Scatter(
                        x=buy_idx,
                        y=df.loc[buy_idx, "Close"],
                        mode="markers",
                        name="Buy",
                        marker=dict(symbol="triangle-up", color="#16a34a", size=10),
                    )
                )
            if not sell_idx.empty:
                fig.add_trace(
                    go.Scatter(
                        x=sell_idx,
                        y=df.loc[sell_idx, "Close"],
                        mode="markers",
                        name="Sell",
                        marker=dict(symbol="triangle-down", color="#dc2626", size=10),
                    )
                )
            if buy_idx.empty and sell_idx.empty:
                st.warning("No se generaron cruces de SMA en el período analizado.")

            fig.update_layout(margin=dict(l=40, r=20, t=40, b=40))
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Métricas")
            metrics_df = pd.DataFrame(metrics, index=[0]).T.rename(columns={0: "Valor"})
            st.dataframe(metrics_df.style.format({"Valor": "{:.4f}"}))

            st.subheader("Curva de equity")
            equity_fig = go.Figure(
                data=[
                    go.Scatter(
                        x=bt.index,
                        y=bt["equity"],
                        mode="lines",
                        name="Equity",
                    )
                ]
            )
            equity_fig.update_layout(margin=dict(l=40, r=20, t=40, b=40))
            st.plotly_chart(equity_fig, use_container_width=True)
else:
    st.write("Esperando parámetros para ejecutar el backtest.")
