"""SMA heatmap optimisation page."""
from __future__ import annotations

from datetime import date, timedelta

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
    st.warning("La fecha 'Desde' debe ser anterior a 'Hasta'.")
    st.stop()

windows = list(range(w_min, w_max + 1, step))

with st.spinner("Descargando precios…"):
    prices = load_prices(ticker, start, end)
if prices.empty:
    st.error("No hay datos para ese ticker/rango.")
    st.stop()

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

from quantboard.data import get_prices
from quantboard.optimize import grid_search_sma
from quantboard.plots import heatmap_metric
from quantboard.ui.theme import apply_global_theme

st.set_page_config(page_title="SMA Heatmap", page_icon="🔥", layout="wide")
apply_global_theme()


def _validate_prices(df: pd.DataFrame) -> pd.Series | None:
    """Return a cleaned *close* series or ``None`` when empty."""
    if df.empty or "close" not in df.columns:
        st.error("No data for the selected range/interval.")
        return None

    close = pd.to_numeric(df["close"], errors="coerce").dropna()
    if close.empty:
        st.error("No data for the selected range/interval.")
        return None

    return close


@st.cache_data(ttl=60)
def _load_prices(ticker: str, start: date, end: date) -> pd.DataFrame:
    return get_prices(ticker, start=start, end=end, interval="1d")


def main() -> None:
    st.title("🔥 SMA Heatmap")

    with st.sidebar:
        st.header("Parameters")
        with st.form("heatmap_form"):
            ticker = st.text_input("Ticker", value="AAPL").strip().upper()
            end = st.date_input("To", value=date.today())
            start = st.date_input("From", value=date.today() - timedelta(days=365 * 2))
            fast_min, fast_max = st.slider("Fast SMA range", 5, 60, (10, 25))
            slow_min, slow_max = st.slider("Slow SMA range", 20, 240, (50, 120))
            submitted = st.form_submit_button("Run search", type="primary")

    if not submitted:
        st.info("Choose parameters and click **Run search**.")
        return

    if fast_min >= slow_min:
        st.error("Fast SMA range must stay below the Slow SMA range.")
        return

    with st.spinner("Fetching data..."):
        df = _load_prices(ticker, start=start, end=end)

    close = _validate_prices(df)
    if close is None:
        return

    with st.spinner("Scanning for optimal combinations..."):
        z = grid_search_sma(
            close,
            fast_range=range(int(fast_min), int(fast_max) + 1),
            slow_range=range(int(slow_min), int(slow_max) + 1),
            metric="Sharpe",
        )

    # Invalidate combinations where fast >= slow
    for fast_window in z.index:
        for slow_window in z.columns:
            if int(fast_window) >= int(slow_window):
                z.loc[fast_window, slow_window] = float("nan")

    st.subheader("Heatmap (Sharpe)")
    st.plotly_chart(heatmap_metric(z, title="SMA grid — Sharpe"), use_container_width=True)

    stacked = z.stack().dropna().astype(float)
    if stacked.empty:
        st.warning("No valid combination found in the selected range.")
        return

    f_best, s_best = map(int, stacked.idxmax())
    st.success(f"Best combo: **Fast SMA {f_best} / Slow SMA {s_best}**")

    top_df = (
        stacked.sort_values(ascending=False)
        .head(10)
        .rename_axis(("fast", "slow"))
        .reset_index(name="Sharpe")
    )

    st.subheader(f"Top {len(top_df)} combinations")
    header_cols = st.columns([1, 1, 1, 1.5])
    header_cols[0].markdown("**Fast**")
    header_cols[1].markdown("**Slow**")
    header_cols[2].markdown("**Sharpe**")
    header_cols[3].markdown("**Action**")

    for idx, row in top_df.iterrows():
        fast_val = int(row["fast"])
        slow_val = int(row["slow"])
        sharpe_val = float(row["Sharpe"])
        cols = st.columns([1, 1, 1, 1.5])
        cols[0].write(fast_val)
        cols[1].write(slow_val)
        cols[2].write(f"{sharpe_val:.2f}")
        if cols[3].button("Run Backtest", key=f"run_backtest_{idx}"):
            st.query_params["ticker"] = ticker
            st.query_params["fast"] = str(fast_val)
            st.query_params["slow"] = str(slow_val)
            try:
                st.switch_page("pages/03_Backtest.py")
            except Exception:  # pragma: no cover - depends on Streamlit runtime
                st.info("Open Backtest from the menu; the parameters were set.")

    if st.button("Use in Home"):
        st.query_params["ticker"] = ticker
        try:
            st.switch_page("streamlit_app.py")
        except Exception:  # pragma: no cover - depends on Streamlit runtime
            st.info("Open Home from the menu; the ticker was set.")


main()
