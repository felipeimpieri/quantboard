"""Página de backtest para estrategia SMA crossover."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quantboard.backtest import run_backtest, sma_crossover_signals
from quantboard.data import get_prices


st.set_page_config(page_title="Backtest SMA", page_icon="🧪", layout="wide")

st.title("Backtest SMA crossover")
st.info("Ingresá los parámetros en la barra lateral y ejecutá el backtest.")

st.sidebar.header("Parámetros")
ticker = st.sidebar.text_input("Ticker", value="AAPL")
start_default = date.today() - timedelta(days=365 * 2)
start = st.sidebar.date_input("Desde", value=start_default)
end = st.sidebar.date_input("Hasta", value=date.today())
interval = st.sidebar.selectbox("Intervalo", options=["1d"], index=0, disabled=True)
fast = st.sidebar.number_input("SMA rápida", min_value=2, max_value=200, value=20, step=1)
slow = st.sidebar.number_input("SMA lenta", min_value=3, max_value=400, value=50, step=1)
run_btn = st.sidebar.button("Correr backtest", type="primary")

if run_btn:
    if not ticker.strip():
        st.error("Ingresá un ticker válido.")
    elif start >= end:
        st.error("La fecha 'Desde' debe ser anterior a 'Hasta'.")
    elif int(fast) >= int(slow):
        st.error("La SMA rápida debe ser menor que la SMA lenta.")
    else:
        prices = pd.DataFrame()
        metrics: dict[str, float] = {}
        signal = pd.Series(dtype=float)
        overlays: dict[str, pd.Series] = {}
        bt = pd.DataFrame()
        error_msg: str | None = None

        with st.spinner("Descargando datos y ejecutando backtest..."):
            try:
                prices = get_prices(
                    ticker.strip(),
                    start=start.isoformat(),
                    end=end.isoformat(),
                    interval=interval,
                )
            except Exception as exc:  # seguridad ante errores inesperados
                error_msg = str(exc)
                prices = pd.DataFrame()

            if error_msg is None and not prices.empty:
                close = prices.get("Close", pd.Series(dtype=float)).dropna()
                if close.empty:
                    error_msg = "No se encontraron precios de cierre para el ticker." 
                else:
                    signal, overlays = sma_crossover_signals(close, fast=int(fast), slow=int(slow))
                    bt, metrics = run_backtest(prices.loc[close.index], signal, interval=interval)

        if error_msg:
            st.error(error_msg)
        elif prices.empty or metrics == {}:
            st.error("No se pudieron obtener datos para el ticker y rango seleccionados.")
        else:
            st.subheader("Precio y señales")
            fig = go.Figure()
            fig.add_trace(
                go.Candlestick(
                    x=prices.index,
                    open=prices["Open"],
                    high=prices["High"],
                    low=prices["Low"],
                    close=prices["Close"],
                    name="Precio",
                )
            )

            for name, series in overlays.items():
                if series is not None and not series.dropna().empty:
                    fig.add_trace(
                        go.Scatter(
                            x=series.index,
                            y=series.values,
                            mode="lines",
                            name=name,
                        )
                    )

            signal_change = signal.diff().fillna(0)
            buy_mask = signal_change > 0
            sell_mask = signal_change < 0
            buy_idx = buy_mask[buy_mask].index
            sell_idx = sell_mask[sell_mask].index

            if not buy_idx.empty:
                fig.add_trace(
                    go.Scatter(
                        x=buy_idx,
                        y=prices.loc[buy_idx, "Close"],
                        mode="markers",
                        name="Buy",
                        marker=dict(symbol="triangle-up", color="#16a34a", size=10),
                    )
                )
            if not sell_idx.empty:
                fig.add_trace(
                    go.Scatter(
                        x=sell_idx,
                        y=prices.loc[sell_idx, "Close"],
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
            metrics_df = (
                pd.DataFrame(metrics, index=[0]).T.rename(columns={0: "Valor"}).sort_index()
            )
            st.dataframe(metrics_df.style.format({"Valor": "{:.4f}"}))

            st.subheader("Curva de equity")
            equity_fig = go.Figure()
            equity_fig.add_trace(
                go.Scatter(
                    x=bt.index,
                    y=bt["equity"],
                    mode="lines",
                    name="Equity",
                )
            )
            equity_fig.update_layout(margin=dict(l=40, r=20, t=40, b=40))
            st.plotly_chart(equity_fig, use_container_width=True)
else:
    st.write("Ingresá los parámetros y presioná *Correr backtest* para comenzar.")
