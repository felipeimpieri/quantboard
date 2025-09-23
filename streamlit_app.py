import streamlit as st

st.set_page_config(page_title="QuantBoard v0.2", page_icon="📈", layout="wide")

params = st.experimental_get_query_params()
ticker = params.get("ticker", [None])[0]

st.title("QuantBoard")
if ticker:
    st.write(f"Ticker seleccionado: {ticker}")
else:
    st.write("Seleccioná una página desde el menú para empezar.")
