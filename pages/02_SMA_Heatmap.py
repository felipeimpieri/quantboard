# pages/02_SMA_Heatmap.py
"""SMA Heatmap — grid search for fast/slow SMA parameters."""

from __future__ import annotations
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

from quantboard.data import get_prices
from quantboard.optimize import grid_search_sma
from quantboard.plots import heatmap_metric

st.set_page_config(page_title="SMA Heatmap", page_icon="🔥", layout="wide")
st.title("SMA Heatmap")

with st.sidebar:
    st.header("Parameters")
    ticker = st.text_input("Ticker", value="AAPL").strip().upper()

    st.subheader("Ranges")
    fast_min, fast_max = st.slider("Fast SMA range", min_value=5, max_value=60, value=(10, 30))
    slow_min, slow_max = st.slider("Slow SMA range", min_value=20, max_value=200, value=(50, 120))

    calc_btn = st.button("Calculate", type="primary")

st.info("Pick ranges and press **Calculate**. Only valid pairs with fast < slow are considered.")

if calc_btn:
    with st.spinner("Downloading data..."):
        end = datetime.today().date()
        start = (datetime.today() - timedelta(days=365)).date()
        df = get_prices(ticker, start=start, end=end, interval="1d")

    if df.empty or "close" not in df.columns:
        st.error("No data for the selected range/interval or missing 'close' column.")
        st.stop()

    close = pd.to_numeric(df["close"], errors="coerce").dropna()
    if close.empty:
        st.error("No valid closing prices to compute the grid.")
        st.stop()

    fast_rng = range(int(fast_min), int(fast_max) + 1)
    slow_rng = range(int(slow_min), int(slow_max) + 1)

    z = grid_search_sma(
        close,
        fast_range=fast_rng,
        slow_range=slow_rng,
        metric="Sharpe",
    )

    # blank fast>=slow
    z = z.copy()
    for f in list(z.index):
        for s in list(z.columns):
            if f >= s:
                z.loc[f, s] = float("nan")

    st.subheader("Sharpe heatmap")
    fig = heatmap_metric(z, title=f"{ticker} — SMA Grid (Sharpe)")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        st.caption("Higher is better. Hover cells to inspect the pair.")
    with c2:
        if st.button("Open in Home"):
            st.experimental_set_query_params(ticker=ticker)
            try:
                st.switch_page("streamlit_app.py")
            except Exception:
                st.success("Ticker set on Home. Go back to the main page from the menu.")

