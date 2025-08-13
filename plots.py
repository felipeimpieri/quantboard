import plotly.graph_objs as go
import pandas as pd

def price_chart(df: pd.DataFrame, show_sma: bool = True, sma_fast: int = 20, sma_slow: int = 50):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="Precio"
    ))
    if show_sma:
        if f"SMA_{sma_fast}" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[f"SMA_{sma_fast}"], mode="lines", name=f"SMA {sma_fast}"))
        if f"SMA_{sma_slow}" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[f"SMA_{sma_slow}"], mode="lines", name=f"SMA {sma_slow}"))
    fig.update_layout(height=500, margin=dict(l=10,r=10,t=30,b=10), xaxis_title=None, yaxis_title=None)
    return fig
