"""Página para explorar combinaciones de SMA rápida y lenta."""

from datetime import date, timedelta

import plotly.express as px
import streamlit as st

from quantboard.data import get_prices
from quantboard.heatmap import sma_grid_heatmap


st.set_page_config(page_title="SMA Heatmap", page_icon="🔥", layout="wide")

st.title("SMA Heatmap")
st.info("Configurar rangos y presionar **Calcular** para ver el heatmap.")

st.sidebar.header("Parámetros")
ticker = st.sidebar.text_input("Ticker", value="AAPL")
fmin = st.sidebar.number_input("SMA rápida mínima", 1, 200, 5)
fmax = st.sidebar.number_input("SMA rápida máxima", 1, 200, 20)
smin = st.sidebar.number_input("SMA lenta mínima", 5, 400, 30)
smax = st.sidebar.number_input("SMA lenta máxima", 5, 400, 100)
metric = st.sidebar.selectbox("Métrica", ["CAGR", "Sharpe"], index=0)
calc_btn = st.sidebar.button("Calcular", type="primary")

if calc_btn:
    start = date.today() - timedelta(days=730)
    end = date.today()
    with st.spinner("Descargando datos..."):
        df = get_prices(ticker, start=start, end=end, interval="1d")

    if df.empty:
        st.error("No se pudieron obtener datos históricos para el ticker seleccionado.")
        st.stop()

    close = df.get("close")
    if close is None or close.dropna().empty:
        st.error("Los datos descargados no contienen precios de cierre válidos.")
        st.stop()

    z = sma_grid_heatmap(
        close.dropna(),
        fast_range=range(int(fmin), int(fmax) + 1),
        slow_range=range(int(smin), int(smax) + 1),
        metric=metric,
    )

    st.subheader(f"Heatmap {metric}")
    fig = px.imshow(
        z,
        labels=dict(x="SMA lenta", y="SMA rápida", color=metric),
        text_auto=".2f",
    )
    st.plotly_chart(fig, use_container_width=True)

    stacked = z.stack(dropna=True)
    if not stacked.empty:
        (best_fast, best_slow) = stacked.idxmax()
        best_val = z.loc[best_fast, best_slow]
        st.success(
            f"Mejor {metric}: {best_val:.4f} con SMA rápida {best_fast} y lenta {best_slow}"
        )
        if st.button("Usar en Home con este ticker"):
            st.experimental_set_query_params(ticker=ticker)
            st.switch_page("streamlit_app.py")
    else:
        st.warning("No hay combinaciones válidas para los rangos seleccionados.")

