from __future__ import annotations

from datetime import date, datetime, timedelta
import time
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from quantboard.data import get_prices
from quantboard.indicators import sma, rsi
from quantboard.plots import apply_plotly_theme
from quantboard.ui.theme import apply_global_theme

st.set_page_config(page_title="QuantBoard", page_icon="📈", layout="wide")
apply_global_theme()

# --- Auto-refresh (every 60s) for 1m interval ---
def _autorefresh_if_needed(enabled: bool, interval: str) -> None:
    if not enabled or interval != "1m":
        return
    key = "_qb_autorefresh_last"
    now = time.time()
    last = st.session_state.get(key, 0.0)
    if now - last >= 60.0:
        st.session_state[key] = now
        st.rerun()

@st.cache_data(ttl=60, show_spinner=False)
def fetch_prices_cached(ticker: str, start: date | datetime, end: date | datetime, interval: str) -> pd.DataFrame:
    df = get_prices((ticker or "").strip().upper(), start=start, end=end, interval=interval)
    if df is None or df.empty:
        return pd.DataFrame()
    # normaliza a minúscula
    df = df.rename(columns=str.lower)
    df.index = pd.to_datetime(df.index)
    return df.dropna()

def main() -> None:
    st.title("QuantBoard — Real-time Technical Analysis")
    st.caption("Configure the sidebar to load prices and indicators. **Intraday 1m** with **60s auto-refresh**.")

    today = date.today()
    default_start = today - timedelta(days=365)

    with st.sidebar:
        st.header("Parameters")
        ticker = st.text_input("Ticker", value="AAPL").strip().upper()
        start_date = st.date_input("From", value=default_start, max_value=today)
        end_date = st.date_input("To", value=today, min_value=default_start, max_value=today)
        interval = st.selectbox("Interval", ["1d", "1h", "1wk", "1m"], index=0)
        auto_refresh = st.checkbox("Auto-refresh 1m", value=False, help="Refreshes every 60 seconds when 1m interval is selected.")

    if start_date > end_date:
        st.error("The 'From' date must be earlier than 'To'.")
        return

    _autorefresh_if_needed(auto_refresh, interval)

    if not ticker:
        st.info("Enter a ticker to begin.")
        return

    with st.spinner("Fetching data..."):
        prices = fetch_prices_cached(ticker, start=start_date, end=end_date, interval=interval)

    if prices.empty or "close" not in prices.columns:
        st.error("No data for the selected range/interval.")
        return

    close = pd.to_numeric(prices["close"], errors="coerce")
    latest_ts = prices.index[-1]
    latest_price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2]) if len(close) > 1 else float("nan")
    delta = latest_price - prev_price if pd.notna(prev_price) else 0.0
    pct = (delta / prev_price * 100.0) if pd.notna(prev_price) and prev_price != 0 else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Last Price", f"{latest_price:,.2f}", f"{delta:+,.2f}" if pd.notna(prev_price) else None)
    c2.metric("Change %", f"{pct:+.2f}%" if pd.notna(prev_price) else "N/A")
    c3.metric("Last Bar", latest_ts.strftime("%Y-%m-%d %H:%M:%S"))

    st.caption(f"Loaded candles: {len(prices):,}")

    tab_price, tab_ind = st.tabs(["Price", "Indicators"])
    with tab_price:
        st.subheader("Price chart")
        fig = go.Figure()
        fig.add_candlestick(
            x=prices.index,
            open=prices.get("open", prices["close"]),
            high=prices.get("high", prices["close"]),
            low=prices.get("low", prices["close"]),
            close=prices["close"],
            name="OHLC",
        )
        apply_plotly_theme(fig)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(prices.tail(50), use_container_width=True)

    with tab_ind:
        st.subheader("SMA/RSI indicators")
        col_sma, col_rsi = st.columns(2)
        sma_win = col_sma.slider("SMA window", 5, 200, 20, 1)
        rsi_win = col_rsi.slider("RSI window", 2, 50, 14, 1)

        sma_ser = sma(close, int(sma_win))
        rsi_ser = rsi(close, window=int(rsi_win))

        g = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.07, row_heights=[0.65, 0.35])
        g.add_trace(go.Scatter(x=prices.index, y=close, mode="lines", name="Close"), row=1, col=1)
        g.add_trace(go.Scatter(x=sma_ser.index, y=sma_ser, mode="lines", name=f"SMA {sma_win}"), row=1, col=1)
        g.add_trace(go.Scatter(x=rsi_ser.index, y=rsi_ser, mode="lines", name=f"RSI {rsi_win}"), row=2, col=1)
        g.add_hline(y=70, line_dash="dot", row=2, col=1)
        g.add_hline(y=30, line_dash="dot", row=2, col=1)
        g.update_layout(margin=dict(l=30, r=20, t=30, b=30), height=600)
        apply_plotly_theme(g)
        st.plotly_chart(g, use_container_width=True)


if __name__ == "__main__":
    main()

