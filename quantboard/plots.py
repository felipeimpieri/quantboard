"""Plot helpers for QuantBoard visualisations."""
from __future__ import annotations

from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd


THEME_COLORWAY = [
    "#F97316",
    "#34D399",
    "#F87171",
    "#60A5FA",
    "#FBBF24",
    "#A78BFA",
]


def apply_plotly_theme(fig: go.Figure) -> go.Figure:
    """Apply the QuantBoard Plotly styling to a figure."""

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0F1115",
        font=dict(color="#E5E7EB"),
        colorway=THEME_COLORWAY,
    )
    fig.update_xaxes(gridcolor="#2A2F37", zeroline=False)
    fig.update_yaxes(gridcolor="#2A2F37", zeroline=False)
    return fig


def price_chart(df: pd.DataFrame, overlays: dict | None = None) -> go.Figure:
    overlays = overlays or {}
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])

    lookup = {col.lower(): col for col in df.columns}
    open_col = lookup.get("open", "open")
    high_col = lookup.get("high", "high")
    low_col = lookup.get("low", "low")
    close_col = lookup.get("close", "close")

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df[open_col],
            high=df[high_col],
            low=df[low_col],
            close=df[close_col],
            name="OHLC",
        ),
        row=1,
        col=1,
    )

    # Overlays: SMAs/EMA
    for key in ("SMA_fast", "SMA_slow", "EMA"):
        ser = overlays.get(key)
        if ser is not None:
            fig.add_trace(go.Scatter(x=ser.index, y=ser.values, mode="lines", name=key), row=1, col=1)

    # Bollinger
    bb = overlays.get("BB")
    if isinstance(bb, pd.DataFrame) and {"BB_upper", "BB_mid", "BB_lower"}.issubset(bb.columns):
        fig.add_trace(go.Scatter(x=bb.index, y=bb["BB_upper"], mode="lines", name="BB_upper"), row=1, col=1)
        fig.add_trace(go.Scatter(x=bb.index, y=bb["BB_mid"], mode="lines", name="BB_mid"), row=1, col=1)
        fig.add_trace(go.Scatter(x=bb.index, y=bb["BB_lower"], mode="lines", name="BB_lower"), row=1, col=1)

    # RSI
    rsi_ser = overlays.get("RSI")
    if rsi_ser is not None:
        fig.add_trace(go.Scatter(x=rsi_ser.index, y=rsi_ser.values, mode="lines", name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", row=2, col=1)

    fig.update_layout(margin=dict(l=40, r=20, t=40, b=40))
    return apply_plotly_theme(fig)


def fig_price(
    df: pd.DataFrame,
    overlays: dict[str, pd.Series | pd.DataFrame] | None = None,
    close_col: str = "close",
) -> go.Figure:
    """Plot price information as candlesticks or a line with optional overlays."""

    fig = go.Figure()

    if df is None or df.empty:
        fig.update_layout(
            margin=dict(l=40, r=20, t=40, b=40),
            height=600,
            xaxis_title="Date",
            yaxis_title="Price",
        )
        return apply_plotly_theme(fig)

    data = df.copy()
    data.index = pd.to_datetime(data.index)

    overlays = overlays or {}

    column_lookup = {col.lower(): col for col in data.columns}
    required_ohlc = {"open", "high", "low", "close"}
    has_ohlc = required_ohlc.issubset(column_lookup.keys())
    close_key = column_lookup.get(close_col.lower(), close_col)

    if has_ohlc:
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data[column_lookup["open"]],
                high=data[column_lookup["high"]],
                low=data[column_lookup["low"]],
                close=data[column_lookup["close"]],
                name="OHLC",
            )
        )
    elif close_key in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data[close_key],
                mode="lines",
                name="Close",
            )
        )
    else:
        raise ValueError("DataFrame must include OHLC columns or a valid close column.")

    for name, series in overlays.items():
        if series is None:
            continue
        if isinstance(series, pd.DataFrame):
            for sub_name, ser in series.items():
                cleaned = ser.copy()
                cleaned.index = pd.to_datetime(cleaned.index)
                fig.add_trace(
                    go.Scatter(
                        x=cleaned.index,
                        y=cleaned.values,
                        mode="lines",
                        name=f"{name} ({sub_name})",
                    )
                )
            continue

        ser = series.copy()
        ser.index = pd.to_datetime(ser.index)
        fig.add_trace(
            go.Scatter(x=ser.index, y=ser.values, mode="lines", name=name)
        )

    fig.update_layout(
        margin=dict(l=40, r=20, t=40, b=40),
        height=600,
        xaxis_title="Date",
        yaxis_title="Price",
    )
    return apply_plotly_theme(fig)


def heatmap_metric(z_df: pd.DataFrame, title: str = "SMA grid (metric)") -> go.Figure:
    fig = go.Figure(
        data=go.Heatmap(
            z=z_df.values,
            x=z_df.columns,
            y=z_df.index,
            colorbar=dict(title="Metric"),
            hovertemplate="Fast %{y}<br>Slow %{x}<br>Value %{z:.4f}<extra></extra>",
        )
    )
    fig.update_layout(title=title, xaxis_title="Slow", yaxis_title="Fast")
    return apply_plotly_theme(fig)


__all__ = ["price_chart", "heatmap_metric", "fig_price", "apply_plotly_theme"]
