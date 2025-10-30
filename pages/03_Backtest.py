import datetime as dt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quantboard.backtest import run_backtest
from quantboard.data import get_prices
from quantboard.indicators import sma
from quantboard.plots import apply_plotly_theme
from quantboard.ui.theme import apply_global_theme

try:
    from quantboard.strategies import signals_sma_crossover
except Exception:  # pragma: no cover - optional dependency guard
    signals_sma_crossover = None  # type: ignore[assignment]
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


def _clean_prices(df: pd.DataFrame) -> pd.DataFrame | None:
    price_cols = ["open", "high", "low", "close", "volume"]
    numeric = {col: pd.to_numeric(df.get(col), errors="coerce") for col in price_cols if col in df}
    clean = df.assign(**numeric).dropna(subset=["close"])
    if clean.empty:
        st.error("No price data available after cleaning.")
        return None
    return clean


def _run_signals(close: pd.Series, fast: int, slow: int) -> pd.Series:
    if signals_sma_crossover is not None:
        sig, _ = signals_sma_crossover(close, fast=fast, slow=slow)
        return sig

    sma_fast = sma(close, fast)
    sma_slow = sma(close, slow)
    cross_up = (sma_fast > sma_slow) & (sma_fast.shift(1) <= sma_slow.shift(1))
    cross_dn = (sma_fast < sma_slow) & (sma_fast.shift(1) >= sma_slow.shift(1))
    sig = pd.Series(0.0, index=close.index)
    sig = sig.where(~cross_up, 1.0)
    sig = sig.where(~cross_dn, -1.0)
    return sig.replace(0, pd.NA).ffill().fillna(0.0)


def main() -> None:
    st.title("Backtest — SMA crossover")

    with st.sidebar:
        st.header("Parameters")
        with st.form("backtest_form"):
            ticker = st.text_input("Ticker", value="AAPL").strip().upper()
            end = st.date_input("To", value=date.today())
            start = st.date_input("From", value=date.today() - timedelta(days=365 * 2))
            interval = st.selectbox("Interval", ["1d", "1h", "1wk", "1m"], index=0)
            fast = st.number_input("Fast SMA", 5, 200, 20, step=1)
            slow = st.number_input("Slow SMA", 10, 400, 50, step=1)
            fee_bps = st.number_input("Fees (bps)", 0, 50, 0, step=1)
            slip_bps = st.number_input("Slippage (bps)", 0, 50, 0, step=1)
            submitted = st.form_submit_button("Run backtest", type="primary")

    st.info("Configure the sidebar parameters and run the backtest.")

    if not submitted:
        return

    if fast >= slow:
        st.error("Fast SMA must be smaller than Slow SMA.")
        return

    with st.spinner("Fetching data..."):
        df = get_prices(ticker, start=start, end=end, interval=interval)

    df = _validate_prices(df)
    if df is None:
        return

    df = _clean_prices(df)
    if df is None:
        return

    signals = _run_signals(df["close"], fast=int(fast), slow=int(slow))

    bt, metrics = run_backtest(
        df,
        signals=signals,
        fee_bps=int(fee_bps),
        slippage_bps=int(slip_bps),
        interval=interval,
    )

    st.subheader("Price and SMAs")
    sma_fast = sma(df["close"], int(fast))
    sma_slow = sma(df["close"], int(slow))

    price_fig = go.Figure()
    price_fig.add_candlestick(
        x=df.index,
        open=df.get("open", df["close"]),
        high=df.get("high", df["close"]),
        low=df.get("low", df["close"]),
        close=df["close"],
        name="ohlc",
    )
    price_fig.add_trace(
        go.Scatter(x=sma_fast.index, y=sma_fast, mode="lines", name=f"SMA {int(fast)}"),
    )
    price_fig.add_trace(
        go.Scatter(x=sma_slow.index, y=sma_slow, mode="lines", name=f"SMA {int(slow)}"),
    )

    changes = signals.diff().fillna(0)
    buys = df.index[changes > 0]
    sells = df.index[changes < 0]
    price_fig.add_trace(
        go.Scatter(
            x=buys,
            y=df.loc[buys, "close"],
            mode="markers",
            marker_symbol="triangle-up",
            marker_size=10,
            name="Buy",
        ),
    )
    price_fig.add_trace(
        go.Scatter(
            x=sells,
            y=df.loc[sells, "close"],
            mode="markers",
            marker_symbol="triangle-down",
            marker_size=10,
            name="Sell",
        ),
    )

    price_fig.update_layout(margin=dict(l=30, r=20, t=30, b=30), height=520)
    apply_plotly_theme(price_fig)
    st.plotly_chart(price_fig, use_container_width=True)

    st.subheader("Equity curve")
    eq_fig = go.Figure(go.Scatter(x=bt.index, y=bt["equity"], mode="lines", name="Equity"))
    eq_fig.update_layout(margin=dict(l=30, r=20, t=30, b=30), height=320)
    apply_plotly_theme(eq_fig)
    st.plotly_chart(eq_fig, use_container_width=True)

    st.subheader("Metrics")
    metrics_order = [
        "CAGR",
        "Sharpe",
        "Sortino",
        "Max Drawdown",
        "Win rate",
        "Avg trade return",
        "Exposure (%)",
        "Trades count",
    ]
    percent_metrics = {
        "CAGR",
        "Max Drawdown",
        "Win rate",
        "Avg trade return",
        "Exposure (%)",
    }
    ratio_metrics = {"Sharpe", "Sortino"}

    metrics_rows = []
    for key in metrics_order:
        value = metrics.get(key, 0.0)
        if key == "Trades count":
            display = f"{int(value)}"
        elif key in percent_metrics:
            display = f"{value:.2%}"
        elif key in ratio_metrics:
            display = f"{value:.2f}"
        else:
            display = f"{value:.4f}"
        metrics_rows.append({"Metric": key, "Value": display})

    metrics_df = pd.DataFrame(metrics_rows).set_index("Metric")
    st.dataframe(metrics_df, use_container_width=True)


main()
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
