"""Watchlist page to manage favourite tickers."""
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

from quantboard.data import get_prices
from quantboard.features.watchlist import load_watchlist, save_watchlist
from quantboard.ui.theme import apply_global_theme

st.set_page_config(page_title="Watchlist", page_icon="👀", layout="wide")
apply_global_theme()

st.title("Watchlist")

watchlist = load_watchlist()

st.sidebar.header("Parameters")
new_ticker = st.sidebar.text_input("Add ticker")
if st.sidebar.button("Add"):
    ticker = new_ticker.strip().upper()
    if ticker and ticker not in watchlist:
        watchlist.append(ticker)
        save_watchlist(watchlist)
        st.rerun()

if watchlist:
    st.sidebar.subheader("Remove")
    for t in list(watchlist):
        if st.sidebar.button(f"❌ {t}", key=f"rm_{t}"):
            watchlist.remove(t)
            save_watchlist(watchlist)
            st.rerun()

    @st.cache_data(ttl=60, show_spinner=False)
    def load_data(tickers: list[str]) -> pd.DataFrame:
        rows: list[dict[str, float | str]] = []
        start = (datetime.today() - timedelta(days=30)).date()
        end = datetime.today().date()
        for tick in tickers:
            df = get_prices(tick, start=start, end=end, interval="1d")
            if df.empty or "close" not in df.columns:
                continue
            close = pd.to_numeric(df["close"], errors="coerce").dropna()
            if close.empty:
                continue
            last_price = float(close.iloc[-1])
            first_price = float(close.iloc[0])
            pct_30d = ((last_price / first_price) - 1.0) * 100.0 if first_price else 0.0
            rows.append({"Ticker": tick, "Last price": last_price, "30d %": pct_30d})
        return pd.DataFrame(rows)

    df = load_data(watchlist)

    if df.empty:
        st.info("Unable to fetch prices.")
    else:
        for _, row in df.iterrows():
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            c1.write(row["Ticker"])
            c2.write(f"{row['Last price']:.2f}")
            c3.write(f"{row['30d %']:.2f}%")
            if c4.button("Open in Home", key=f"open_{row['Ticker']}"):
                st.query_params["ticker"] = row["Ticker"]
                try:
                    st.switch_page("streamlit_app.py")
                except Exception:
                    st.info("Open Home from the menu; the ticker was set.")
else:
    st.info("Add tickers from the sidebar.")

