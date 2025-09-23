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

# --- Auto-refresh helper (usa paquete si está, si no, fallback simple) ---
try:
    from streamlit_autorefresh import st_autorefresh  # type: ignore
except Exception:
    def st_autorefresh(interval: int = 0, limit: int | None = None, key: str | None = None) -> int:  # type: ignore
        if interval <= 0:
            return 0
        key = key or "autorefresh"
        counter_key, last_key = f"_{key}_count", f"_{key}_last"
        now = time.time()
        count = st.session_state.get(counter_key, 0)
        last_run = st.session_state.get(last_key)
        if last_run is None:
            st.session_state[last_key] = now
        elif (now - last_run) * 1000 >= interval and (limit is None or count < limit):
            st.session_state[last_key] = now
            st.session_state[counter_key] = count + 1
            if hasattr(st, "rerun") and callable(st.rerun):
                st.rerun()
        return st.session_state.get(counter_key, 0)

# --- Datos (cache 60s) ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_prices(ticker: str, start: date | datetime, end: date | datetime, interval: str) -> pd.DataFrame:
    t = (ticker or "").strip().upper()
    if not t:
        return pd.DataFrame()

    start_dt = datetime.combine(start, datetime.min.time()) if isinstance(start, date) and not isinstance(start, datetime) else pd.to_datetime(start)
    end_dt   = datetime.combine(end,   datetime.max.time()) if isinstance(end,   date) and not isinstance(end,   datetime) else pd.to_datetime(end)
    if pd.isna(start_dt) or pd.isna(end_dt) or start_dt >= end_dt:
        return pd.DataFrame()

    try:
        df = yf.download(t, start=start_dt, end=end_dt, interval=interval, auto_adjust=True, progress=False)
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        try:
            df = df.xs(t, axis=1, level=1)
        except Exception:
            df = df.droplevel(0, axis=1)

    df = df.rename(columns=str.lower)
    df.index = pd.to_datetime(df.index)
    return df.dropna()

def format_ts(ts: pd.Timestamp) -> str:
    if pd.isna(ts):
        return "-"
    return ts.tz_localize(None).strftime("%Y-%m-%d %H:%M:%S") if getattr(ts, "tzinfo", None) else ts.strftime("%Y-%m-%d %H:%M:%S")

def main() -> None:
    st.title("QuantBoard — Análisis técnico en tiempo real")
    st.caption("Configurá la barra lateral y obtené precios/indicadores. Intradía 1m con auto-refresco de 60s.")

    today = date.today()
    default_start = today - timedelta(days=365)

    # Sidebar
    with st.sidebar:
        st.header("Parámetros")
        ticker = st.text_input("Ticker", value="AAPL").strip().upper()
        start_date = st.date_input("Desde", value=default_start, max_value=today)
        end_date   = st.date_input("Hasta", value=today, min_value=default_start, max_value=today)
        interval = st.selectbox("Intervalo", ["1d", "1h", "1wk", "1m"], index=0)
        auto_refresh = st.checkbox("Auto-refrescar 1m", value=False, help="Rerun automático cada 60 segundos si el intervalo es 1m.")

        if auto_refresh and interval != "1m":
            st.info("El auto-refresco sólo aplica cuando el intervalo es 1m.")

    if start_date > end_date:
        st.error("La fecha 'Desde' debe ser anterior a 'Hasta'.")
        return

    if auto_refresh and interval == "1m" and runtime.exists():
        st_autorefresh(interval=60_000, key="autorefresh_1m")

    if not ticker:
        st.info("Ingresá un ticker para comenzar.")
        return

    with st.spinner("Descargando datos..."):
        prices = fetch_prices(ticker, start=start_date, end=end_date, interval=interval)

    if prices.empty:
        st.error("No hay datos para el rango/intervalo seleccionado.")
        return

    close = prices["close"]
    latest_ts = prices.index[-1]
    latest = float(close.iloc[-1])
    prev = float(close.iloc[-2]) if len(close) > 1 else float("nan")
    delta = latest - prev if not pd.isna(prev) else 0.0
    pct   = (delta / prev * 100) if (prev and not pd.isna(prev) and prev != 0) else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Último", f"{latest:,.2f}", f"{delta:+,.2f}" if not pd.isna(prev) else None)
    c2.metric("Variación %", f"{pct:+.2f}%" if not pd.isna(prev) else "N/A")
    c3.metric("Última vela", format_ts(latest_ts))

    st.caption(f"Histórico cargado: {len(prices):,} velas")

    tab_price, tab_ind = st.tabs(["Precio", "Indicadores"])

    with tab_price:
        st.subheader("Gráfico de precio")
        st.plotly_chart(fig_price(prices[["open","high","low","close"]]), use_container_width=True)
        st.dataframe(prices.tail(50), use_container_width=True)

    with tab_ind:
        st.subheader("SMA / RSI")
        col_sma, col_rsi = st.columns(2)
        sma_window = col_sma.slider("Período SMA", 5, 200, 20)
        rsi_period = col_rsi.slider("Período RSI", 2, 50, 14)

        sma_series = sma(close, window=int(sma_window))
        # Nota: usamos 'window' para compatibilidad con quantboard.indicators.rsi
        rsi_series = rsi(close, window=int(rsi_period))

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.07, row_heights=[0.65, 0.35])
        fig.add_trace(go.Scatter(x=close.index, y=close.values, mode="lines", name="Close"), row=1, col=1)
        fig.add_trace(go.Scatter(x=sma_series.index, y=sma_series.values, mode="lines", name=f"SMA {sma_window}"), row=1, col=1)
        fig.add_trace(go.Scatter(x=rsi_series.index, y=rsi_series.values, mode="lines", name=f"RSI {rsi_period}"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", row=2, col=1)
        fig.update_layout(height=600, margin=dict(l=40, r=20, t=40, b=40))
        st.plotly_chart(fig, use_container_width=True)

        k1, k2 = st.columns(2)
        k1.metric("SMA actual", f"{sma_series.iloc[-1]:,.2f}" if not sma_series.empty else "N/A")
        k2.metric("RSI actual", f"{rsi_series.iloc[-1]:.2f}" if not rsi_series.empty else "N/A")

    st.caption("Con intervalo 1m y auto-refresco activo, se actualiza cada 60s (cache de 60s para no sobrecargar yfinance).")

if __name__ == "__main__":
    main()
