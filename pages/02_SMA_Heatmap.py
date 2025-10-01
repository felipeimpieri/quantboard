from datetime import date, timedelta

import pandas as pd
import streamlit as st

from quantboard.data import get_prices
from quantboard.optimize import grid_search_sma
from quantboard.plots import heatmap_metric

st.set_page_config(page_title="SMA Heatmap", page_icon="🔥", layout="wide")


def _validate_prices(df: pd.DataFrame) -> pd.Series | None:
    if df.empty or "close" not in df.columns:
        st.error("No data for selected range/interval.")
        return None
    close = pd.to_numeric(df["close"], errors="coerce").dropna()
    if close.empty:
        st.error("No data for selected range/interval.")
        return None
    return close


def main() -> None:
    st.title("🔥 SMA Heatmap")

    with st.sidebar:
        st.header("Parámetros")
        ticker = st.text_input("Ticker", value="AAPL").strip().upper()
        end = st.date_input("Hasta", value=date.today())
        start = st.date_input("Desde", value=date.today() - timedelta(days=365 * 2))
        fast_min, fast_max = st.slider("Rango SMA rápida", 5, 60, (10, 25))
        slow_min, slow_max = st.slider("Rango SMA lenta", 20, 240, (50, 120))
        run_btn = st.button("Calcular", type="primary")

    if not run_btn:
        st.info("Elegí parámetros y apretá **Calcular**.")
        return

    with st.spinner("Descargando datos..."):
        df = get_prices(ticker, start=start, end=end, interval="1d")

    close = _validate_prices(df)
    if close is None:
        return

    with st.spinner("Buscando mejores combinaciones..."):
        z = grid_search_sma(
            close,
            fast_range=range(int(fast_min), int(fast_max) + 1),
            slow_range=range(int(slow_min), int(slow_max) + 1),
            metric="Sharpe",
        )
        # Invalida combinaciones fast>=slow
        for f in z.index:
            for s in z.columns:
                if int(f) >= int(s):
                    z.loc[f, s] = float("nan")

    st.subheader("Mapa de calor (Sharpe)")
    st.plotly_chart(heatmap_metric(z, title="SMA grid – Sharpe"), use_container_width=True)

    # Mejor combinación (ignorando NaNs)
    best = z.stack().dropna().astype(float).idxmax() if z.stack().dropna().size else None
    if best:
        f_best, s_best = map(int, best)
        st.success(f"Mejor combinación: **SMA rápida {f_best} / SMA lenta {s_best}**")
        if st.button("Usar en Home"):
            st.experimental_set_query_params(ticker=ticker)
            try:
                st.switch_page("streamlit_app.py")
            except Exception:
                st.info("Volvé a Home desde el menú; el ticker quedó seteado.")
    else:
        st.warning("No se encontró una combinación válida en el rango elegido.")


main()
