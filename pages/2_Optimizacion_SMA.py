import streamlit as st
from datetime import date, timedelta

# QuantBoard package
from quantboard.data import get_prices
from quantboard.optimize import grid_search_sma
from quantboard.plots import heatmap_metric

# Página dedicada a la grid search de SMA
st.set_page_config(page_title="QuantBoard v0.2", page_icon="📈", layout="wide")

st.title("Optimización SMA")
st.info("Configurar los parámetros y presionar **Optimizar grid**.")

# --- Sidebar ---
st.sidebar.header("Configuración")

ticker = st.sidebar.text_input("Ticker", value="AAPL")
end = st.sidebar.date_input("Hasta", value=date.today())
start = st.sidebar.date_input("Desde", value=date.today() - timedelta(days=365))
interval = st.sidebar.selectbox("Intervalo", options=["1m", "1d", "1wk", "1mo"], index=1)

st.sidebar.markdown("---")
fee_bps = st.sidebar.number_input("Comisión (bps)", min_value=0, max_value=50, value=0)
slip_bps = st.sidebar.number_input("Slippage (bps)", min_value=0, max_value=50, value=0)
fast_min, fast_max = st.sidebar.slider("Rango SMA rápida", 5, 50, (10, 20))
slow_min, slow_max = st.sidebar.slider("Rango SMA lenta", 20, 200, (50, 100))
opt_btn = st.sidebar.button("Optimizar grid", type="primary")

# --- Optimization grid ---
if opt_btn:
    with st.spinner("Buscando parámetros (SMA grid)..."):
        df = get_prices(ticker, start=start, end=end, interval=interval)
        close = df.get("close") if not df.empty else None
        if close is None or close.dropna().empty:
            st.error("No se pudieron obtener precios de cierre válidos para el ticker.")
            st.stop()
        z = grid_search_sma(
            close.dropna(),
            fast_range=range(int(fast_min), int(fast_max) + 1),
            slow_range=range(int(slow_min), int(slow_max) + 1),
            fee_bps=int(fee_bps),
            slippage_bps=int(slip_bps),
            interval=interval,
            metric="Sharpe",
        )
    st.subheader("SMA grid (Sharpe)")
    st.plotly_chart(heatmap_metric(z, title="SMA grid – Sharpe"), use_container_width=True)


