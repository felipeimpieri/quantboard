"""Página de backtest para estrategia SMA crossover."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quantboard.backtest import run_backtest
from quantboard.data import get_prices
from quantboard.indicators import sma

try:
    from quantboard.strategies import signals_sma_crossover
except Exception:  # pragma: no cover - fallback cuando no está el módulo
    signals_sma_crossover = None  # type: ignore[assignment]

st.set_page_config(page_title="Backtest", page_icon="🧪", layout="wide")


def _validate_prices(df: pd.DataFrame) -> pd.DataFrame | None:
    if df.empty or "close" not in df.columns:
        st.error("No data for selected range/interval.")
        return None
    return df


def main() -> None:
    st.title("🧪 Backtest SMA crossover")

    with st.sidebar:
        st.header("Parámetros")
        ticker = st.text_input("Ticker", value="AAPL").strip().upper()
        end = st.date_input("Hasta", value=date.today())
        start = st.date_input("Desde", value=date.today() - timedelta(days=365 * 2))
        interval = st.selectbox("Intervalo", ["1d", "1h", "1wk", "1m"], index=0)
        fast = st.number_input("SMA rápida", 5, 200, 20, step=1)
        slow = st.number_input("SMA lenta", 10, 400, 50, step=1)
        fee_bps = st.number_input("Comisión (bps)", 0, 50, 0, step=1)
        slip_bps = st.number_input("Slippage (bps)", 0, 50, 0, step=1)
        run_btn = st.button("Ejecutar backtest", type="primary")

    st.info("Ingresá los parámetros en la barra lateral y ejecutá el backtest.")

    if not run_btn:
        return

    with st.spinner("Descargando datos..."):
        df = get_prices(ticker, start=start, end=end, interval=interval)

    df = _validate_prices(df)
    if df is None:
        return

    # Series limpias
    close = pd.to_numeric(df["close"], errors="coerce")
    df = df.assign(close=close).dropna(subset=["close"])

    # Señales
    if signals_sma_crossover is not None:
        sig, _ = signals_sma_crossover(df["close"], fast=int(fast), slow=int(slow))
    else:
        # Fallback local si no está el módulo de estrategias
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
    st.subheader("Precio y SMAs")

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

    # Marcas buy/sell
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
            name="Compra",
        )
    )
    price_fig.add_trace(
        go.Scatter(
            x=sells,
            y=df.loc[sells, "close"],
            mode="markers",
            marker_symbol="triangle-down",
            marker_size=10,
            name="Venta",
        )
    )

    price_fig.update_layout(margin=dict(l=30, r=20, t=30, b=30), height=520)
    st.plotly_chart(price_fig, use_container_width=True)

    st.subheader("Curva de equity")
    eq_fig = go.Figure(go.Scatter(x=bt.index, y=bt["equity"], mode="lines", name="Equity"))
    eq_fig.update_layout(margin=dict(l=30, r=20, t=30, b=30), height=320)
    st.plotly_chart(eq_fig, use_container_width=True)

    # Métricas
    st.subheader("Métricas")
    mdf = pd.DataFrame([metrics]).T.rename(columns={0: "value"})
    st.dataframe(mdf.style.format({"value": "{:.4f}"}), use_container_width=True)


main()
