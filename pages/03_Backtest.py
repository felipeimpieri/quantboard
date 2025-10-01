# pages/03_Backtest.py
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

def compute_sma(df: pd.DataFrame, fast: int, slow: int) -> pd.DataFrame:
    out = df.copy()
    out["sma_fast"] = out["close"].rolling(fast, min_periods=fast).mean()
    out["sma_slow"] = out["close"].rolling(slow, min_periods=slow).mean()
    return out

def generate_signals(df: pd.DataFrame) -> pd.Series:
    # 1 = long cuando SMA rápida > SMA lenta
    sig = (df["sma_fast"] > df["sma_slow"]).astype(int)
    return sig

def backtest_equity(df: pd.DataFrame, signal: pd.Series, fee_bp: float = 5.0) -> pd.DataFrame:
    """fee_bp: costo por trade ida+vuelta en basis points (0.01% = 1 bp)."""
    out = df.copy()
    out["signal"] = signal
    out["signal_prev"] = out["signal"].shift(1).fillna(0)
    # Ret del sistema: ret del activo * posicion
    out["strategy_ret"] = out["ret"] * out["signal_prev"]
    # Costos en cambio de señal
    trades = (out["signal"] != out["signal_prev"]).astype(int)
    fee = fee_bp / 10000.0
    out["strategy_ret"] -= trades * fee
    out["equity"] = (1.0 + out["strategy_ret"]).cumprod()
    out["buy_hold"] = (1.0 + out["ret"]).cumprod()
    return out

def metrics(df: pd.DataFrame) -> dict:
    eq = df["equity"].dropna()
    bh = df["buy_hold"].dropna()
    def cagr(series: pd.Series) -> float:
        if series.empty: return np.nan
        n_years = (series.index[-1] - series.index[0]).days / 365.25
        return series.iloc[-1] ** (1 / max(n_years, 1e-9)) - 1
    def max_dd(series: pd.Series) -> float:
        peak = series.cummax()
        dd = series / peak - 1
        return dd.min()
    def sharpe(rets: pd.Series) -> float:
        if rets.std() == 0: return np.nan
        return (rets.mean() / rets.std()) * np.sqrt(252)
    return {
        "CAGR Strategy": cagr(eq),
        "CAGR Buy&Hold": cagr(bh),
        "Max Drawdown Strat": max_dd(eq),
        "Max Drawdown B&H": max_dd(bh),
        "Sharpe Strat": sharpe(df["strategy_ret"].dropna()),
        "Trades": int((df["signal"] != df["signal_prev"]).sum()),
    }

with st.sidebar:
    st.subheader("Parámetros")
    ticker = st.text_input("Ticker", value="AAPL").upper().strip()
    col1, col2 = st.columns(2)
    default_end = dt.date.today()
    default_start = default_end - dt.timedelta(days=365 * 5)
    start = col1.date_input("Desde", value=default_start)
    end = col2.date_input("Hasta", value=default_end)
    fast = st.number_input("SMA rápida", min_value=3, max_value=100, value=20)
    slow = st.number_input("SMA lenta", min_value=10, max_value=300, value=100)
    fee_bp = st.number_input("Costo ida+vuelta (bp)", min_value=0.0, max_value=100.0, value=5.0, step=0.5)

if start >= end:
    st.warning("La fecha 'Desde' debe ser anterior a 'Hasta'.")
    st.stop()
if fast >= slow:
    st.warning("La SMA rápida debe ser menor que la lenta.")
    st.stop()

with st.spinner("Descargando precios…"):
    prices = load_prices(ticker, start, end)

if prices.empty:
    st.error("No se encontraron datos para ese ticker / rango.")
    st.stop()

df = compute_sma(prices, fast, slow)
sig = generate_signals(df)
bt = backtest_equity(df, sig, fee_bp=fee_bp)
m = metrics(bt)

# --- Charts
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

st.divider()
st.subheader("Métricas")
colA, colB, colC = st.columns(3)
colA.metric("CAGR Strategy", f"{m['CAGR Strategy']*100:,.2f}%")
colA.metric("CAGR Buy&Hold", f"{m['CAGR Buy&Hold']*100:,.2f}%")
colB.metric("Max DD Strategy", f"{m['Max Drawdown Strat']*100:,.2f}%")
colB.metric("Max DD B&H", f"{m['Max Drawdown B&H']*100:,.2f}%")
colC.metric("Sharpe Strategy", f"{m['Sharpe Strat']:.2f}")
colC.metric("Trades", f"{m['Trades']}")
