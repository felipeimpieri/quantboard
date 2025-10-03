"""Bollinger Bands mean-reversion strategy page."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quantboard.backtest import run_backtest
from quantboard.data import get_prices
from quantboard.plots import apply_plotly_theme
from quantboard.strategies import signals_bollinger_mean_reversion
from quantboard.ui.theme import apply_global_theme

st.set_page_config(page_title="Bollinger Mean Reversion", page_icon="📊", layout="wide")
apply_global_theme()


def _validate_prices(df: pd.DataFrame) -> pd.DataFrame | None:
    if df.empty or "close" not in df.columns:
        st.error("No data for the selected range/interval.")
        return None
    return df


def _clean_prices(df: pd.DataFrame) -> pd.DataFrame | None:
    price_cols = ["open", "high", "low", "close", "volume"]
    numeric = {col: pd.to_numeric(df.get(col), errors="coerce") for col in price_cols if col in df}
    clean = df.assign(**numeric).dropna(subset=["close"])
    if clean.empty:
        st.error("No price data available after cleaning.")
        return None
    return clean


def _price_with_signals(
    df: pd.DataFrame,
    signals: pd.Series,
    overlays: dict[str, pd.Series | pd.DataFrame] | None = None,
) -> go.Figure:
    overlays = overlays or {}
    fig = go.Figure()
    fig.add_candlestick(
        x=df.index,
        open=df.get("open", df["close"]),
        high=df.get("high", df["close"]),
        low=df.get("low", df["close"]),
        close=df["close"],
        name="ohlc",
    )

    for name, series in overlays.items():
        if isinstance(series, pd.DataFrame):
            for sub_name, ser in series.items():
                fig.add_trace(
                    go.Scatter(x=ser.index, y=ser.values, mode="lines", name=f"{name} ({sub_name})"),
                )
        elif series is not None:
            fig.add_trace(go.Scatter(x=series.index, y=series.values, mode="lines", name=name))

    changes = signals.diff().fillna(signals.iloc[0] if len(signals) else 0.0)
    buys = df.index[changes > 0]
    sells = df.index[changes < 0]

    if len(buys):
        fig.add_trace(
            go.Scatter(
                x=buys,
                y=df.loc[buys, "close"],
                mode="markers",
                marker_symbol="triangle-up",
                marker_size=10,
                name="Buy",
            ),
        )
    if len(sells):
        fig.add_trace(
            go.Scatter(
                x=sells,
                y=df.loc[sells, "close"],
                mode="markers",
                marker_symbol="triangle-down",
                marker_size=10,
                name="Sell",
            ),
        )

    fig.update_layout(margin=dict(l=30, r=20, t=30, b=30), height=520)
    return apply_plotly_theme(fig)


def main() -> None:
    st.title("Backtest — Bollinger mean reversion")

    with st.sidebar:
        st.header("Parameters")
        with st.form("bb_form"):
            ticker = st.text_input("Ticker", value="AAPL").strip().upper()
            end = st.date_input("To", value=date.today())
            start = st.date_input("From", value=date.today() - timedelta(days=365 * 2))
            interval = st.selectbox("Interval", ["1d", "1h", "1wk"], index=0)
            window = st.number_input("Window", 5, 200, 20, step=1)
            n_std = st.number_input("Std dev", 1.0, 5.0, 2.0, step=0.5)
            fee_bps = st.number_input("Fees (bps)", 0, 50, 0, step=1)
            slip_bps = st.number_input("Slippage (bps)", 0, 50, 0, step=1)
            submitted = st.form_submit_button("Run backtest", type="primary")

    st.info("Configure the sidebar parameters and run the backtest.")

    if not submitted:
        return

    with st.spinner("Fetching data..."):
        df = get_prices(ticker, start=start, end=end, interval=interval)

    df = _validate_prices(df)
    if df is None:
        return

    df = _clean_prices(df)
    if df is None:
        return

    signals, overlays = signals_bollinger_mean_reversion(
        df["close"],
        window=int(window),
        n_std=float(n_std),
    )

    bt, metrics = run_backtest(
        df,
        signals=signals,
        fee_bps=int(fee_bps),
        slippage_bps=int(slip_bps),
        interval=interval,
    )

    st.subheader("Price and bands")
    price_fig = _price_with_signals(df, signals, overlays)
    st.plotly_chart(price_fig, use_container_width=True)

    st.subheader("Equity curve")
    eq_fig = go.Figure(go.Scatter(x=bt.index, y=bt["equity"], mode="lines", name="Equity"))
    eq_fig.update_layout(margin=dict(l=30, r=20, t=30, b=30), height=320)
    apply_plotly_theme(eq_fig)
    st.plotly_chart(eq_fig, use_container_width=True)

    st.subheader("Metrics")
    metrics_df = pd.DataFrame([metrics]).T.rename(columns={0: "Value"})
    st.dataframe(metrics_df.style.format({"Value": "{:.4f}"}), use_container_width=True)


main()
