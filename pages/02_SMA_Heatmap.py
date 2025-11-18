"""SMA heatmap optimisation page."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from quantboard.data import get_prices_cached
from quantboard.optimize import grid_search_sma
from quantboard.plots import heatmap_metric
from quantboard.ui.state import get_param, set_param, shareable_link_button
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
    return get_prices_cached(ticker, start=start, end=end, interval="1d")


def main() -> None:
    st.title("🔥 SMA Heatmap")

    shareable_link_button()

    today = date.today()
    default_start = today - timedelta(days=365 * 2)

    ticker_default = str(get_param("ticker", "AAPL")).strip().upper() or "AAPL"
    end_default = get_param("heat_end", today)
    start_default = get_param("heat_start", default_start)
    fast_min_default = int(get_param("heat_fast_min", 10))
    fast_max_default = int(get_param("heat_fast_max", 25))
    slow_min_default = int(get_param("heat_slow_min", 50))
    slow_max_default = int(get_param("heat_slow_max", 120))

    fast_min_default = max(5, min(60, fast_min_default))
    fast_max_default = max(fast_min_default, min(60, fast_max_default))
    slow_min_default = max(20, min(240, slow_min_default))
    slow_max_default = max(slow_min_default, min(240, slow_max_default))

    with st.sidebar:
        st.header("Parameters")
        with st.form("heatmap_form"):
            ticker = st.text_input("Ticker", value=ticker_default).strip().upper()
            end = st.date_input("To", value=end_default)
            start = st.date_input("From", value=start_default)
            fast_min, fast_max = st.slider("Fast SMA range", 5, 60, (fast_min_default, fast_max_default))
            slow_min, slow_max = st.slider("Slow SMA range", 20, 240, (slow_min_default, slow_max_default))
            submitted = st.form_submit_button("Run search", type="primary")

    if not submitted:
        st.info("Choose parameters and click **Run search**.")
        return

    set_param("ticker", ticker or None)
    set_param("heat_end", end)
    set_param("heat_start", start)
    set_param("heat_fast_min", int(fast_min))
    set_param("heat_fast_max", int(fast_max))
    set_param("heat_slow_min", int(slow_min))
    set_param("heat_slow_max", int(slow_max))

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
            set_param("ticker", ticker or None)
            set_param("fast", int(fast_val))
            set_param("slow", int(slow_val))
            try:
                st.switch_page("pages/03_Backtest.py")
            except Exception:  # pragma: no cover - depends on Streamlit runtime
                st.info("Open Backtest from the menu; the parameters were set.")

    if st.button("Use in Home"):
        set_param("ticker", ticker or None)
        try:
            st.switch_page("streamlit_app.py")
        except Exception:  # pragma: no cover - depends on Streamlit runtime
            st.info("Open Home from the menu; the ticker was set.")


main()
