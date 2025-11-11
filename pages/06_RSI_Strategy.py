"""RSI strategy backtest page."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quantboard.backtest import run_backtest
from quantboard.data import get_prices
from quantboard.indicators import rsi
from quantboard.plots import apply_plotly_theme
from quantboard.ui.theme import apply_global_theme

st.set_page_config(page_title="RSI Strategy", page_icon="📈", layout="wide")
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
                name="Sell/Short",
            ),
        )

    fig.update_layout(margin=dict(l=30, r=20, t=30, b=30), height=520)
    return apply_plotly_theme(fig)


def _build_signals(
    close: pd.Series,
    *,
    period: int,
    lower: float,
    upper: float,
    mode: str,
) -> tuple[pd.Series, dict[str, pd.Series]]:
    rsi_series = rsi(close, window=period)
    go_long = (rsi_series.shift(1) < lower) & (rsi_series >= lower)
    go_flat = (rsi_series.shift(1) > upper) & (rsi_series <= upper)

    signals = pd.Series(index=close.index, dtype=float)
    signals.loc[go_long] = 1.0

    if mode == "Long only":
        signals.loc[go_flat] = 0.0
    else:
        signals.loc[go_flat] = -1.0

    signals = signals.ffill().fillna(0.0)

    if mode == "Long only":
        signals = signals.clip(lower=0.0, upper=1.0)
    else:
        signals = signals.clip(-1.0, 1.0)

    return signals, {"RSI": rsi_series}


def main() -> None:
    st.title("Backtest — RSI strategy")

    with st.sidebar:
        st.header("Parameters")
        with st.form("rsi_form"):
            ticker = st.text_input("Ticker", value="AAPL").strip().upper()
            end = st.date_input("To", value=date.today())
            start = st.date_input("From", value=date.today() - timedelta(days=365 * 2))
            interval = st.selectbox("Interval", ["1d", "1h", "1wk"], index=0)
            period = st.number_input("RSI period", 2, 100, 14, step=1)
            lower = st.number_input("Lower threshold", 0, 100, 30, step=1)
            upper = st.number_input("Upper threshold", 0, 100, 70, step=1)
            mode = st.selectbox("Signal mode", ["Long only", "Flip long/short"], index=0)
            fee_bps = st.number_input("Fees (bps)", 0, 50, 0, step=1)
            slip_bps = st.number_input("Slippage (bps)", 0, 50, 0, step=1)
            submitted = st.form_submit_button("Run backtest", type="primary")

    st.info("Configure the sidebar parameters and run the backtest.")

    if not submitted:
        return

    if lower >= upper:
        st.error("Lower threshold must be less than Upper threshold.")
        return

    with st.spinner("Fetching data..."):
        df = get_prices(ticker, start=start, end=end, interval=interval)

    df = _validate_prices(df)
    if df is None:
        return

    df = _clean_prices(df)
    if df is None:
        return

    signals, overlays = _build_signals(
        df["close"],
        period=int(period),
        lower=float(lower),
        upper=float(upper),
        mode=mode,
    )

    bt, metrics = run_backtest(
        df,
        signals=signals,
        fee_bps=int(fee_bps),
        slippage_bps=int(slip_bps),
        interval=interval,
    )

    st.subheader("Price and signals")
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
