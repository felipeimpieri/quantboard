import datetime as dt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Backtest", page_icon="🧪", layout="wide")
st.title("🧪 Backtest — SMA Crossover")

@st.cache_data(show_spinner=False)
def load_prices(ticker: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if df.empty:
        return df
    df = df[["Close"]].rename(columns={"Close": "close"}).dropna()
    df["ret"] = df["close"].pct_change().fillna(0.0)
    return df

def add_smas(df: pd.DataFrame, fast: int, slow: int) -> pd.DataFrame:
    out = df.copy()
    out["sma_fast"] = out["close"].rolling(fast, min_periods=fast).mean()
    out["sma_slow"] = out["close"].rolling(slow, min_periods=slow).mean()
    return out

def signals(df: pd.DataFrame) -> pd.Series:
    return (df["sma_fast"] > df["sma_slow"]).astype(int)

def backtest(df: pd.DataFrame, sig: pd.Series, fee_bp: float = 5.0) -> pd.DataFrame:
    out = df.copy()
    out["signal"] = sig
    out["signal_prev"] = out["signal"].shift(1).fillna(0)
    out["str_ret"] = out["ret"] * out["signal_prev"]
    fee = (out["signal"] != out["signal_prev"]).astype(int) * (fee_bp / 10000.0)
    out["str_ret"] -= fee
    out["equity"] = (1 + out["str_ret"]).cumprod()
    out["buy_hold"] = (1 + out["ret"]).cumprod()
    return out

def cagr(series: pd.Series) -> float:
    if series.empty: return np.nan
    years = (series.index[-1] - series.index[0]).days / 365.25
    return series.iloc[-1] ** (1/max(years, 1e-9)) - 1

def max_dd(series: pd.Series) -> float:
    peak = series.cummax()
    dd = series/peak - 1
    return float(dd.min())

def sharpe(returns: pd.Series) -> float:
    r = returns.dropna()
    if r.std() == 0: return np.nan
    return (r.mean()/r.std()) * np.sqrt(252)

# ------- UI -------
with st.sidebar:
    st.subheader("Parámetros")
    ticker = st.text_input("Ticker", "AAPL").strip().upper()
    col1, col2 = st.columns(2)
    end = col2.date_input("Hasta", value=dt.date.today())
    start = col1.date_input("Desde", value=end - dt.timedelta(days=365*5))
    fast = st.number_input("SMA rápida", 3, 100, 20)
    slow = st.number_input("SMA lenta", 10, 300, 100)
    fee_bp = st.number_input("Costo ida+vuelta (bp)", 0.0, 100.0, 5.0, step=0.5)

if start >= end:
    st.warning("La fecha 'Desde' debe ser anterior a 'Hasta'.")
    st.stop()
if fast >= slow:
    st.warning("La SMA rápida debe ser menor que la lenta.")
    st.stop()

with st.spinner("Descargando precios…"):
    px_df = load_prices(ticker, start, end)
if px_df.empty:
    st.error("No hay datos para ese ticker/rango.")
    st.stop()

df = add_smas(px_df, fast, slow)
sig = signals(df)
bt = backtest(df, sig, fee_bp)

# ------- Charts -------
c1, c2 = st.columns(2)
with c1:
    st.subheader("Precio + SMAs")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=bt.index, y=bt["close"], name="Close"))
    fig.add_trace(go.Scatter(x=bt.index, y=bt["sma_fast"], name=f"SMA {fast}"))
    fig.add_trace(go.Scatter(x=bt.index, y=bt["sma_slow"], name=f"SMA {slow}"))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Equity Curve (Strategy vs Buy&Hold)")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=bt.index, y=bt["equity"], name="Strategy"))
    fig2.add_trace(go.Scatter(x=bt.index, y=bt["buy_hold"], name="Buy&Hold"))
    st.plotly_chart(fig2, use_container_width=True)

# ------- Métricas -------
st.divider()
st.subheader("Métricas")
colA, colB, colC = st.columns(3)
colA.metric("CAGR Strategy", f"{cagr(bt['equity'])*100:,.2f}%")
colA.metric("CAGR Buy&Hold", f"{cagr(bt['buy_hold'])*100:,.2f}%")
colB.metric("Max DD Strategy", f"{max_dd(bt['equity'])*100:,.2f}%")
colB.metric("Max DD B&H", f"{max_dd(bt['buy_hold'])*100:,.2f}%")
colC.metric("Sharpe Strategy", f"{sharpe(bt['str_ret']):.2f}")
colC.metric("Trades", int((bt['signal'] != bt['signal_prev']).sum()))
