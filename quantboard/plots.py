from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd

def price_chart(df: pd.DataFrame, overlays: dict | None = None) -> go.Figure:
    overlays = overlays or {}
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])

    # OHLC
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="OHLC"
        ),
        row=1, col=1,
    )

    # Overlays: SMAs/EMA
    for key in ("SMA_fast", "SMA_slow", "EMA"):
        ser = overlays.get(key)
        if ser is not None:
            fig.add_trace(go.Scatter(x=ser.index, y=ser.values, mode="lines", name=key), row=1, col=1)

    # Bollinger
    bb = overlays.get("BB")
    if isinstance(bb, pd.DataFrame) and {"BB_upper","BB_mid","BB_lower"}.issubset(bb.columns):
        fig.add_trace(go.Scatter(x=bb.index, y=bb["BB_upper"], mode="lines", name="BB_upper"), row=1, col=1)
        fig.add_trace(go.Scatter(x=bb.index, y=bb["BB_mid"],   mode="lines", name="BB_mid"),   row=1, col=1)
        fig.add_trace(go.Scatter(x=bb.index, y=bb["BB_lower"], mode="lines", name="BB_lower"), row=1, col=1)

    # RSI
    rsi_ser = overlays.get("RSI")
    if rsi_ser is not None:
        fig.add_trace(go.Scatter(x=rsi_ser.index, y=rsi_ser.values, mode="lines", name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", row=2, col=1)

    fig.update_layout(margin=dict(l=40, r=20, t=40, b=40))
    return fig

def fig_price(df: pd.DataFrame, overlays: dict | None = None) -> go.Figure:
    """Wrapper around :func:`price_chart` that tolerates lowercase OHLC columns."""

    if df is None or df.empty:
        return go.Figure()

    overlays = overlays or {}

    rename_map: dict[str, str] = {}
    for col in df.columns:
        lower = col.lower()
        if lower in {"open", "high", "low", "close"}:
            rename_map[col] = lower.capitalize()

    normalized = df.rename(columns=rename_map).copy()

    required = {"Open", "High", "Low", "Close"}
    if not required.issubset(normalized.columns):
        missing = ", ".join(sorted(required - set(normalized.columns)))
        raise ValueError(f"Missing OHLC columns for fig_price: {missing}")

    normalized = normalized[["Open", "High", "Low", "Close"]]
    normalized.index = pd.to_datetime(normalized.index)

    cleaned_overlays: dict[str, pd.Series | pd.DataFrame] = {}
    for key, value in overlays.items():
        if isinstance(value, pd.Series):
            ser = value.copy()
            ser.index = pd.to_datetime(ser.index)
            cleaned_overlays[key] = ser
        elif isinstance(value, pd.DataFrame):
            df_value = value.copy()
            df_value.index = pd.to_datetime(df_value.index)
            cleaned_overlays[key] = df_value
        else:
            cleaned_overlays[key] = value

    return price_chart(normalized, cleaned_overlays)


def heatmap_metric(z_df: pd.DataFrame, title: str = "SMA grid (metric)") -> go.Figure:
    fig = go.Figure(data=go.Heatmap(z=z_df.values, x=z_df.columns, y=z_df.index, colorbar=dict(title="Metric")))
    fig.update_layout(title=title, xaxis_title="Slow", yaxis_title="Fast")
    return fig

__all__ = ["price_chart", "heatmap_metric", "fig_price"]
