import streamlit as st

from quantboard.ui.state import shareable_link_button

st.set_page_config(page_title="Optimize SMA", page_icon="⚙️", layout="wide")
st.title("⚙️ Optimize SMA")

shareable_link_button()

st.info(
    "This page was replaced by **SMA Heatmap**. "
    "Use the *SMA Heatmap* menu item to optimize parameters."
)
