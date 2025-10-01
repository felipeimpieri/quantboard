# pages/02_SMA_Heatmap.py
import datetime as dt
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

def fwd_return(close: pd.Series, horizon: int) -> pd.Series:
    return close.shift(-horizon) / close - 1

def build_stats(df: pd.DataFrame, windows: list[int], horizon: int) -> pd.DataFrame:
    out = []
    fr = fwd_return(df["close"], horizon)
    for w in windows:
        sma = df["close"].rolling(w, min_periods=w).mean()
        above = fr[(df["close"] > sma)]
        below = fr[(df["close"] <= sma)]
        out.append({
            "window": w,
            "ret_above": float(np.nanmean(above)),
            "ret_below": float(np.nanmean(below)),
        })
    return pd.DataFrame(out)

# ------- UI -------
with st.sidebar:
    st.subheader("Parámetros")
    ticker = st.text_input("Ticker", "AAPL").strip().upper()
    col1, col2 = st.columns(2)
    end = col2.date_input("Hasta", value=dt.date.today())
    start = col1.date_input("Desde", value=end - dt.timedelta(days=365*2))
    w_min, w_max = st.slider("SMA (min–max)", 5, 200, (10, 100))
    step = st.number_input("Paso", 1, 20, 5)
    horizon = st.number_input("Horizonte (días)", 1, 60, 10)

if start >= end:
    st.warning("La fecha 'Desde' debe ser anterior a 'Hasta'."); st.stop()

windows = list(range(w_min, w_max + 1, step))

with st.spinner("Descargando precios…"):
    prices = load_prices(ticker, start, end)
if prices.empty:
    st.error("No hay datos para ese ticker/rango."); st.stop()

stats = build_stats(prices, windows, horizon)

c1, c2 = st.columns(2)
with c1:
    st.subheader(f"Retorno medio futuro {horizon}d cuando **precio > SMA**")
    fig1 = px.imshow(
        np.array([stats["ret_above"].values]),
        aspect="auto", origin="lower", color_continuous_scale="RdBu",
        labels=dict(color=f"Ret {horizon}d")
    )
    fig1.update_xaxes(tickmode="array",
                      tickvals=list(range(len(windows))),
                      ticktext=[str(w) for w in windows],
                      title="SMA window")
    fig1.update_yaxes(visible=False)
    st.plotly_chart(fig1, use_container_width=True)

with c2:
    st.subheader(f"Retorno medio futuro {horizon}d cuando **precio ≤ SMA**")
    fig2 = px.imshow(
        np.array([stats["ret_below"].values]),
        aspect="auto", origin="lower", color_continuous_scale="RdBu",
        labels=dict(color=f"Ret {horizon}d")
    )
    fig2.update_xaxes(tickmode="array",
                      tickvals=list(range(len(windows))),
                      ticktext=[str(w) for w in windows],
                      title="SMA window")
    fig2.update_yaxes(visible=False)
    st.plotly_chart(fig2, use_container_width=True)

st.caption("Rojo = promedio positivo; Azul = promedio negativo. Muestra cómo se comportó el retorno futuro "
           "según estar por encima o por debajo de cada SMA.")
