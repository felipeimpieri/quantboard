"""RSI strategy backtest page."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quantboard.backtest import run_backtest
from quantboard.data import get_prices_cached
from quantboard.indicators import rsi
from quantboard.plots import apply_plotly_theme
from quantboard.ui.state import get_param, set_param, shareable_link_button
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

    shareable_link_button()

    today = date.today()
    default_start = today - timedelta(days=365 * 2)

    ticker_default = str(get_param("ticker", "AAPL")).strip().upper() or "AAPL"
    end_default = get_param("rsi_end", today)
    start_default = get_param("rsi_start", default_start)
    interval_options = ["1d", "1h", "1wk"]
    interval_default = str(get_param("interval", "1d"))
    if interval_default not in interval_options:
        interval_default = "1d"
    period_default = int(get_param("rsi_period", 14))
    lower_default = int(get_param("rsi_lower", 30))
    upper_default = int(get_param("rsi_upper", 70))
    mode_default = str(get_param("rsi_mode", "Long only"))
    fee_default = int(get_param("rsi_fee_bps", 0))
    slip_default = int(get_param("rsi_slippage_bps", 0))

    period_default = max(2, min(100, period_default))
    lower_default = max(0, min(100, lower_default))
    upper_default = max(lower_default + 1, min(100, upper_default))
    if mode_default not in ["Long only", "Flip long/short"]:
        mode_default = "Long only"
    fee_default = max(0, min(50, fee_default))
    slip_default = max(0, min(50, slip_default))

    with st.sidebar:
        st.header("Parameters")
        with st.form("rsi_form"):
            ticker = st.text_input("Ticker", value=ticker_default).strip().upper()
            end = st.date_input("To", value=end_default)
            start = st.date_input("From", value=start_default)
            interval = st.selectbox("Interval", interval_options, index=interval_options.index(interval_default))
            period = st.number_input("RSI period", 2, 100, int(period_default), step=1)
            lower = st.number_input("Lower threshold", 0, 100, int(lower_default), step=1)
            upper = st.number_input("Upper threshold", 0, 100, int(upper_default), step=1)
            mode = st.selectbox("Signal mode", ["Long only", "Flip long/short"], index=["Long only", "Flip long/short"].index(mode_default))
            fee_bps = st.number_input("Fees (bps)", 0, 50, int(fee_default), step=1)
            slip_bps = st.number_input("Slippage (bps)", 0, 50, int(slip_default), step=1)
            submitted = st.form_submit_button("Run backtest", type="primary")

    st.info("Configure the sidebar parameters and run the backtest.")

    if not submitted:
        return

    set_param("ticker", ticker or None)
    set_param("rsi_end", end)
    set_param("rsi_start", start)
    set_param("interval", interval)
    set_param("rsi_period", int(period))
    set_param("rsi_lower", int(lower))
    set_param("rsi_upper", int(upper))
    set_param("rsi_mode", mode)
    set_param("rsi_fee_bps", int(fee_bps))
    set_param("rsi_slippage_bps", int(slip_bps))

    if lower >= upper:
        st.error("Lower threshold must be less than Upper threshold.")
        return

    with st.spinner("Fetching data..."):
        df = get_prices_cached(ticker, start=start, end=end, interval=interval)

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
