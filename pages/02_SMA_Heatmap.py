# pages/02_SMA_Heatmap.py
import datetime as dt
from functools import lru_cache

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="SMA Heatmap", page_icon="📈", layout="wide")
st.title("📈 SMA Heatmap")

@st.cache_data(show_spinner=False)
def load_prices(ticker: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if df.empty:
        return df
    df = df[["Close"]].rename(columns={"Close": "close"}).dropna()
    return df

def compute_sma(df: pd.DataFrame, window: int) -> pd.Series:
    return df["close"].rolling(window, min_periods=window).mean()

def forward_return(df: pd.DataFrame, horizon: int = 10) -> pd.Series:
    # Retorno futuro simple (horizon días)
    return df["close"].shift(-horizon) / df["close"] - 1

def build_heatmap(df: pd.DataFrame, windows: list[int], horizon: int) -> pd.DataFrame:
    out = []
    for w in windows:
        sma = compute_sma(df, w)
        signal = (df["close"] > sma).astype(int)  # 1 si precio > SMA; 0 si no
        fr = forward_return(df, horizon)
        # Retorno medio futuro condicionado por estado del SMA
        up_ret = fr[signal == 1].mean()
        down_ret = fr[signal == 0].mean()
        out.append({"window": w, "ret_when_above": up_ret, "ret_when_below": down_ret})
    return pd.DataFrame(out)

with st.sidebar:
    st.subheader("Parámetros")
    ticker = st.text_input("Ticker", value="AAPL").upper().strip()
    col1, col2 = st.columns(2)
    default_end = dt.date.today()
    default_start = default_end - dt.timedelta(days=365 * 2)
    start = col1.date_input("Desde", value=default_start)
    end = col2.date_input("Hasta", value=default_end)

    w_min, w_max = st.slider("Ventanas SMA (min–max)", 5, 200, (10, 100))
    step = st.number_input("Paso", min_value=1, max_value=20, value=5)
    horizon = st.number_input("Horizonte retorno futuro (días)", min_value=1, max_value=60, value=10)

if start >= end:
    st.warning("La fecha 'Desde' debe ser anterior a 'Hasta'.")
    st.stop()

windows = list(range(w_min, w_max + 1, step))

with st.spinner("Descargando precios…"):
    prices = load_prices(ticker, start, end)

if prices.empty:
    st.error("No se encontraron datos para ese ticker / rango.")
    st.stop()

df_stats = build_heatmap(prices, windows, horizon)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Retorno medio futuro cuando **precio > SMA**")
    fig_up = px.density_heatmap(
        df_stats,
        x="window",
        y=["ret_when_above"],
        z="ret_when_above",
        histfunc="avg",
        nbinsx=len(windows),
        labels={"window": "SMA window", "ret_when_above": f"Ret {horizon}d"},
        color_continuous_scale="RdBu",
    )
    # Workaround simple: usar scatter para mostrar como mapa 1D
    fig_up = px.imshow(
        np.array([df_stats["ret_when_above"].values]),
        aspect="auto",
        color_continuous_scale="RdBu",
        origin="lower",
        labels=dict(color=f"Ret {horizon}d"),
    )
    fig_up.update_xaxes(
        tickmode="array", tickvals=list(range(len(windows))), ticktext=[str(w) for w in windows], title="SMA window"
    )
    fig_up.update_yaxes(visible=False)
    st.plotly_chart(fig_up, use_container_width=True)
with c2:
    st.subheader("Retorno medio futuro cuando **precio ≤ SMA**")
    fig_down = px.imshow(
        np.array([df_stats["ret_when_below"].values]),
        aspect="auto",
        color_continuous_scale="RdBu",
        origin="lower",
        labels=dict(color=f"Ret {horizon}d"),
    )
    fig_down.update_xaxes(
        tickmode="array", tickvals=list(range(len(windows))), ticktext=[str(w) for w in windows], title="SMA window"
    )
    fig_down.update_yaxes(visible=False)
    st.plotly_chart(fig_down, use_container_width=True)

st.divider()
st.write(
    "Interpretación rápida: valores **rojos/positivos** sugieren que, históricamente, estar *por encima* o *por debajo* de ciertas "
    f"ventanas de SMA se asoció con retornos futuros medios **mayores** a {horizon} días; **azules/negativos**, lo contrario."
)

