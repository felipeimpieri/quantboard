"""Utilities for applying the QuantBoard global UI theme."""
from __future__ import annotations

import streamlit as st


CSS = """
<style>
/* Reduce default padding for a denser layout */
main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 1.5rem;
}

/* Sidebar sizing and background consistency */
section[data-testid="stSidebar"] > div {
    background-color: #1A1D23;
}

section[data-testid="stSidebar"] {
    min-width: 320px;
    max-width: 340px;
}

/* Inputs and buttons focus states */
input, textarea, select, button, .stButton button {
    border-radius: 6px !important;
}

.stButton button:focus, .stButton button:hover,
.stDownloadButton button:focus, .stDownloadButton button:hover,
.stSelectbox:focus-within {
    box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.45);
}

/* Dataframe headers */
[data-testid="stDataFrame"] .st-bx {
    background-color: rgba(26, 29, 35, 0.85) !important;
    color: #E5E7EB !important;
    font-weight: 600;
}

/* Tabs accent */
button[data-baseweb="tab"] {
    color: #E5E7EB;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #F97316;
}

/* Metric cards */
[data-testid="metric-container"] {
    background-color: rgba(26, 29, 35, 0.65);
    border: 1px solid #2A2F37;
    border-radius: 12px;
    padding: 1rem;
}

</style>
"""


def apply_global_theme() -> None:
    """Inject base CSS tweaks for the QuantBoard theme."""
    st.markdown(CSS, unsafe_allow_html=True)
