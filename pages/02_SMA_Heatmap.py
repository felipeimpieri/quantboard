"""SMA heatmap optimisation page."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

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

    if st.button("Use in Home"):
        st.experimental_set_query_params(ticker=ticker)
        try:
            st.switch_page("streamlit_app.py")
        except Exception:  # pragma: no cover - depends on Streamlit runtime
            st.info("Open Home from the menu; the ticker was set.")


main()
