"""Trades debug page to inspect trade segmentation."""
from __future__ import annotations

from collections.abc import MutableMapping
from datetime import date, timedelta
from io import StringIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from quantboard.plots import apply_plotly_theme
from quantboard.ui.theme import apply_global_theme

st.set_page_config(page_title="Trades Debug", page_icon="🔎", layout="wide")
apply_global_theme()


def _get_param(params: MutableMapping[str, str], key: str, default: str) -> str:
    value = params.get(key)
    if value is None:
        return default
    return str(value)


def _set_param(params: MutableMapping[str, str], key: str, value: str) -> None:
    if params.get(key) == value:
        return
    params[key] = value


def _parse_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@st.cache_data(ttl=60)
def _load_prices(ticker: str, start: date, end: date) -> pd.DataFrame:
    data = yf.download(
        ticker,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        progress=False,
    )
    if data.empty:
        return data
    data.index = pd.to_datetime(data.index).tz_localize(None)
    data.columns = [str(c).lower() for c in data.columns]
    return data


def _clean_close(df: pd.DataFrame) -> pd.Series | None:
    if df.empty or "close" not in df.columns:
        st.error("No price data available for the selected period.")
        return None
    close = pd.to_numeric(df["close"], errors="coerce").dropna()
    if close.empty:
        st.error("No price data available for the selected period.")
        return None
    return close


def main() -> None:
    st.title("🔎 Trades Debug")

    params = st.query_params
    default_ticker = _get_param(params, "ticker", "AAPL")
    default_fast = _parse_int(_get_param(params, "fast", "20"), 20)
    default_slow = _parse_int(_get_param(params, "slow", "100"), 100)

    with st.sidebar:
        st.header("Parameters")
        ticker_input = st.text_input("Ticker", value=default_ticker).strip().upper()
        fast_input = st.number_input("Fast SMA", min_value=1, max_value=365, value=int(default_fast), step=1)
        slow_input = st.number_input("Slow SMA", min_value=2, max_value=500, value=int(default_slow), step=1)
        lookback_years = st.slider("Lookback (years)", min_value=1, max_value=5, value=2)

    if ticker_input:
        _set_param(params, "ticker", ticker_input)
    ticker = ticker_input or default_ticker

    fast = int(fast_input)
    slow = int(slow_input)

    _set_param(params, "fast", str(fast))
    _set_param(params, "slow", str(slow))

    if fast >= slow:
        st.error("Fast SMA must be strictly lower than Slow SMA.")
        return

    end_date = date.today()
    start_date = end_date - timedelta(days=365 * lookback_years)

    with st.spinner("Downloading price data..."):
        raw = _load_prices(ticker, start=start_date, end=end_date)

    if raw.empty:
        st.warning("No data returned for the selected configuration.")
        return

    close = _clean_close(raw)
    if close is None:
        return

    fast_sma = close.rolling(fast).mean()
    slow_sma = close.rolling(slow).mean()

    signals = pd.Series(0.0, index=close.index)
    valid_mask = fast_sma.notna() & slow_sma.notna()
    signals.loc[valid_mask] = (fast_sma.loc[valid_mask] > slow_sma.loc[valid_mask]).astype(float)

    rets = close.pct_change().fillna(0.0)
    prev_pos = signals.shift(1).fillna(0.0)
    strat_rets = prev_pos * rets

    entries = (signals != 0.0) & (signals != prev_pos)
    # shift trade ids so the flip bar's return stays with the trade that held it
    trade_ids = entries.shift(1).cumsum()
    trade_ids = trade_ids.where(signals != 0.0)
    grouped = (1.0 + strat_rets).groupby(trade_ids)
    trade_returns = grouped.prod() - 1.0
    trade_returns = trade_returns.dropna()

    old_trade_ids = entries.cumsum()
    old_trade_ids = old_trade_ids.where(signals != 0.0)
    old_trade_returns = (1.0 + strat_rets).groupby(old_trade_ids).prod() - 1.0
    old_trade_returns = old_trade_returns.dropna()

    equity_curve = (1.0 + strat_rets).cumprod()

    trades_df = pd.DataFrame({
        "close": close,
        "fast_sma": fast_sma,
        "slow_sma": slow_sma,
        "signal": signals,
        "prev_pos": prev_pos,
        "entries": entries,
        "trade_id": trade_ids,
        "old_trade_id": old_trade_ids,
        "strat_rets": strat_rets,
        "equity": equity_curve,
    })

    st.subheader("Price & Trades")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=close.index,
            y=close.values,
            name="close",
            mode="lines",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=fast_sma.index,
            y=fast_sma.values,
            name=f"Fast SMA {fast}",
            mode="lines",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=slow_sma.index,
            y=slow_sma.values,
            name=f"Slow SMA {slow}",
            mode="lines",
        )
    )

    changes = signals.diff().fillna(signals.iloc[0] if len(signals) else 0.0)
    entry_idx = close.index[changes > 0]
    exit_idx = close.index[changes < 0]

    if len(entry_idx):
        fig.add_trace(
            go.Scatter(
                x=entry_idx,
                y=close.loc[entry_idx],
                mode="markers",
                marker=dict(symbol="triangle-up", size=10, color="#33C472"),
                name="Entry",
            )
        )
    if len(exit_idx):
        fig.add_trace(
            go.Scatter(
                x=exit_idx,
                y=close.loc[exit_idx],
                mode="markers",
                marker=dict(symbol="triangle-down", size=10, color="#FF4B4B"),
                name="Exit",
            )
        )

    trade_rows: list[dict] = []
    new_trades = trades_df.dropna(subset=["trade_id"]).copy()
    if not new_trades.empty:
        new_trades["trade_id"] = new_trades["trade_id"].astype(int)
        for idx, (trade_id, group) in enumerate(new_trades.groupby("trade_id")):
            start_ts = group.index[0]
            end_ts = group.index[-1]
            bars = group.shape[0]
            ret = float((1.0 + group["strat_rets"]).prod() - 1.0)
            equity_end = float(group["equity"].iloc[-1])
            trade_rows.append(
                {
                    "trade_id": int(trade_id),
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                    "bars": bars,
                    "ret_pct": ret * 100.0,
                    "equity": equity_end,
                }
            )
            shade_color = "rgba(51, 196, 114, 0.12)" if idx % 2 == 0 else "rgba(255, 75, 75, 0.12)"
            fig.add_vrect(x0=start_ts, x1=end_ts, fillcolor=shade_color, layer="below", opacity=0.2, line_width=0)

    apply_plotly_theme(fig)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

    if trade_rows:
        trades_table = pd.DataFrame(trade_rows)
        trades_table["start_ts"] = trades_table["start_ts"].dt.strftime("%Y-%m-%d")
        trades_table["end_ts"] = trades_table["end_ts"].dt.strftime("%Y-%m-%d")
        trades_table["ret_pct"] = trades_table["ret_pct"].map(lambda v: f"{v:.2f}%")
        trades_table["equity"] = trades_table["equity"].map(lambda v: f"{v:.3f}")

        st.subheader("Trades (new grouping)")
        st.dataframe(trades_table, use_container_width=True)

        csv_buffer = StringIO()
        pd.DataFrame(trade_rows).to_csv(csv_buffer, index=False)
        st.download_button(
            "Download trades CSV",
            data=csv_buffer.getvalue().encode("utf-8"),
            file_name=f"{ticker}_trades_debug.csv",
            mime="text/csv",
        )
    else:
        st.info("No trades were generated for the current configuration.")

    st.subheader("Old vs New grouping")
    new_count = int(trade_returns.count())
    new_mean = float(trade_returns.mean()) if new_count else 0.0
    new_win_rate = float((trade_returns > 0).mean()) if new_count else 0.0

    old_count = int(old_trade_returns.count())
    old_mean = float(old_trade_returns.mean()) if old_count else 0.0
    old_win_rate = float((old_trade_returns > 0).mean()) if old_count else 0.0

    comparison = pd.DataFrame(
        {
            "Grouping": ["New (shifted)", "Old (unshifted)"],
            "Trades": [new_count, old_count],
            "Mean trade %": [new_mean * 100.0, old_mean * 100.0],
            "Win rate": [new_win_rate, old_win_rate],
        }
    )
    comparison["Mean trade %"] = comparison["Mean trade %"].map(lambda v: f"{v:.2f}%")
    comparison["Win rate"] = comparison["Win rate"].map(lambda v: f"{v:.1%}")
    st.table(comparison)


if __name__ == "__main__":
    main()
