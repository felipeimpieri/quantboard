from __future__ import annotations

import time
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from streamlit import runtime
import yfinance as yf

from quantboard.indicators import sma, rsi
from quantboard.plots import fig_price

st.set_page_config(page_title="QuantBoard v0.2", page_icon="📈", layout="wide")

try:  # Prefer the lightweight built-in helper if available
    from streamlit_autorefresh import st_autorefresh  # type: ignore
except Exception:  # pragma: no cover - fallback when package is missing
    def st_autorefresh(interval: int = 0, limit: int | None = None, key: str | None = None) -> int:  # type: ignore
        """Minimal autorefresh helper relying on ``st.rerun`` as a fallback."""

        if interval <= 0:
            return 0

        key = key or "autorefresh"
        counter_key = f"_{key}_count"
        last_key = f"_{key}_last"

        now = time.time()
        count = st.session_state.get(counter_key, 0)
        last_run = st.session_state.get(last_key)

        if last_run is None:
            st.session_state[last_key] = now
        elif (now - last_run) * 1000 >= interval:
            if limit is None or count < limit:
                st.session_state[last_key] = now
                st.session_state[counter_key] = count + 1
                if hasattr(st, "rerun") and callable(st.rerun):
                    st.rerun()

        return st.session_state.get(counter_key, 0)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_prices(ticker: str, start: date | datetime, end: date | datetime, interval: str) -> pd.DataFrame:
    """Download OHLC data from yfinance with a 60 second cache."""

    ticker = (ticker or "").strip().upper()
    if not ticker:
        return pd.DataFrame()

    if isinstance(start, date) and not isinstance(start, datetime):
        start_dt = datetime.combine(start, datetime.min.time())
    else:
        start_dt = pd.to_datetime(start)

    if isinstance(end, date) and not isinstance(end, datetime):
        end_dt = datetime.combine(end, datetime.max.time())
    else:
        end_dt = pd.to_datetime(end)

    if pd.isna(start_dt) or pd.isna(end_dt) or start_dt >= end_dt:
        return pd.DataFrame()

    try:
        data = yf.download(
            ticker,
            start=start_dt,
            end=end_dt,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
    except Exception:
        return pd.DataFrame()

    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        try:
            data = data.xs(ticker, axis=1, level=1)
        except Exception:
            data = data.droplevel(0, axis=1)

    data = data.rename(columns=str.lower)
    data.index = pd.to_datetime(data.index)

    return data.dropna()


def format_timestamp(ts: pd.Timestamp) -> str:
    if pd.isna(ts):
        return "-"
    return ts.tz_localize(None).strftime("%Y-%m-%d %H:%M:%S") if ts.tzinfo else ts.strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    st.title("QuantBoard — Análisis técnico en tiempo real")
    st.caption("Configurá los parámetros desde la barra lateral para obtener precios y métricas al instante.")

    today = date.today()
    default_start = today - timedelta(days=365)

    with st.sidebar:
        st.header("Parámetros")
        ticker = st.text_input("Ticker", value="AAPL").strip().upper()
        start_date = st.date_input("Desde", value=default_start, max_value=today)
        end_date = st.date_input("Hasta", value=today, min_value=default_start, max_value=today)
        interval = st.selectbox("Intervalo", options=["1d", "1h", "1wk", "1m"], index=0)
        auto_refresh = st.checkbox("Auto-refrescar 1m", value=False, help="Actualiza automáticamente cada 60 segundos en intervalo 1m.")

        if auto_refresh and interval != "1m":
            st.info("El auto-refresco se activa sólo con intervalo 1m.")

    if start_date > end_date:
        st.error("La fecha 'Desde' debe ser anterior a la fecha 'Hasta'.")
        return

    if auto_refresh and interval == "1m" and runtime.exists():
        st_autorefresh(interval=60_000, key="autorefresh_1m")

    if not ticker:
        st.info("Ingresá un ticker para comenzar a analizar.")
        return

    with st.spinner("Descargando datos..."):
        prices = fetch_prices(ticker, start=start_date, end=end_date, interval=interval)

    if prices.empty:
        st.error("No se encontraron datos para el ticker y rango seleccionado. Verificá el símbolo o el intervalo.")
        return

    close = prices["close"]
    latest_ts = prices.index[-1]
    latest_price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2]) if len(close) > 1 else float("nan")
    delta_price = latest_price - prev_price if not pd.isna(prev_price) else 0.0
    pct_change = (delta_price / prev_price * 100) if prev_price and not pd.isna(prev_price) and prev_price != 0 else 0.0

    col_price, col_change, col_time = st.columns(3)
    col_price.metric("Último precio", f"{latest_price:,.2f}", f"{delta_price:+,.2f}" if not pd.isna(prev_price) else None)
    col_change.metric("Variación %", f"{pct_change:+.2f}%" if not pd.isna(prev_price) else "N/A")
    col_time.metric("Última vela", format_timestamp(latest_ts))

    st.caption(f"Datos históricos disponibles: {len(prices):,} velas")

    tab_price, tab_indicators = st.tabs(["Precio", "Indicadores SMA/RSI"])

    with tab_price:
        st.subheader("Gráfico de precio")
        overlays = {}
        st.plotly_chart(fig_price(prices[["open", "high", "low", "close"]], overlays=overlays), use_container_width=True)
        st.dataframe(prices.tail(50), use_container_width=True)

    with tab_indicators:
        st.subheader("Indicadores configurables")
        col_sma, col_rsi = st.columns(2)
        sma_window = col_sma.slider("Período SMA", min_value=5, max_value=200, value=20, step=1)
        rsi_period = col_rsi.slider("Período RSI", min_value=2, max_value=50, value=14, step=1)

        sma_series = sma(close, window=int(sma_window))
        rsi_series = rsi(close, window=int(rsi_period))

        indicator_fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.07, row_heights=[0.65, 0.35])
        indicator_fig.add_trace(
            go.Scatter(x=close.index, y=close.values, mode="lines", name="Close"), row=1, col=1
        )
        indicator_fig.add_trace(
            go.Scatter(x=sma_series.index, y=sma_series.values, mode="lines", name=f"SMA {sma_window}"), row=1, col=1
        )
        indicator_fig.add_trace(
            go.Scatter(x=rsi_series.index, y=rsi_series.values, mode="lines", name=f"RSI {rsi_period}"), row=2, col=1
        )
        indicator_fig.add_hline(y=70, line_dash="dot", row=2, col=1)
        indicator_fig.add_hline(y=30, line_dash="dot", row=2, col=1)
        indicator_fig.update_layout(height=600, margin=dict(l=40, r=20, t=40, b=40))

        st.plotly_chart(indicator_fig, use_container_width=True)

        kpi_col1, kpi_col2 = st.columns(2)
        kpi_col1.metric("SMA actual", f"{sma_series.iloc[-1]:,.2f}" if not sma_series.empty else "N/A")
        kpi_col2.metric("RSI actual", f"{rsi_series.iloc[-1]:.2f}" if not rsi_series.empty else "N/A")

    st.caption("Los datos se actualizan automáticamente cada 60 segundos cuando está habilitado el auto-refresco en intervalo 1m.")


if __name__ == "__main__":
    main()
