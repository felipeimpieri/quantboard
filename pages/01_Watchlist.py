"""Página de Watchlist para seguir tickers y abrirlos en Home."""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from quantboard.data import get_prices
from quantboard.features.watchlist import load_watchlist, save_watchlist

st.set_page_config(page_title="Watchlist", page_icon="👀", layout="wide")

st.title("Watchlist")

watchlist = load_watchlist()

st.sidebar.header("Administrar Watchlist")
new_ticker = st.sidebar.text_input("Agregar ticker")
if st.sidebar.button("Agregar"):
    ticker = new_ticker.strip().upper()
    if ticker and ticker not in watchlist:
        watchlist.append(ticker)
        save_watchlist(watchlist)
        st.experimental_rerun()

if watchlist:
    st.sidebar.subheader("Quitar")
    for t in watchlist:
        if st.sidebar.button(f"❌ {t}", key=f"rm_{t}"):
            watchlist.remove(t)
            save_watchlist(watchlist)
            st.experimental_rerun()

    @st.cache_data(ttl=60, show_spinner=False)
    def load_data(tickers):
        rows = []
        start = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        end = datetime.today().strftime("%Y-%m-%d")
        for tick in tickers:
            df = get_prices(tick, start, end, interval="1d")
            if not df.empty:
                last_price = df["Close"].iloc[-1]
                pct_30d = (last_price / df["Close"].iloc[0] - 1) * 100
                rows.append({"Ticker": tick, "Último precio": last_price, "% 30d": pct_30d})
        return pd.DataFrame(rows)

    df = load_data(watchlist)
    if not df.empty:
        for _, row in df.iterrows():
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            c1.write(row["Ticker"])
            c2.write(f"{row['Último precio']:.2f}")
            c3.write(f"{row['% 30d']:.2f}%")
            if c4.button("Abrir en Home", key=f"open_{row['Ticker']}"):
                st.experimental_set_query_params(ticker=row["Ticker"])
                st.switch_page("streamlit_app.py")
    else:
        st.info("No se pudieron descargar precios.")
else:
    st.info("Agregá tickers desde la barra lateral.")
