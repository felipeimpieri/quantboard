import pandas as pd
from .utils import periods_per_year, compute_cagr, compute_sharpe, max_drawdown

def run_backtest(
    df: pd.DataFrame,
    sig: pd.Series,
    fee_bps: int = 0,
    slippage_bps: int = 0,
    interval: str = "1d",
    stop_atr: float | None = None,  # aceptados pero no usados aún
    tp_atr: float | None = None,
    atr_length: int = 14,
    **kwargs,
):
    """Backtest simple con señal 1/-1/0. Devuelve (result_df, metrics_dict)."""
    prices = df["Close"].astype(float)
    sig = sig.fillna(0).astype(float)

    # Entramos en la barra siguiente
    pos = sig.shift(1).fillna(0)
    ret = prices.pct_change().fillna(0)

    gross = pos * ret
    turnover = pos.diff().abs().fillna(0)
    total_bps = (fee_bps or 0) + (slippage_bps or 0)
    fee = turnover * (total_bps / 10000.0)
    pnl = gross - fee

    equity = (1 + pnl).cumprod()
    ppy = periods_per_year(interval)
    metrics = {
        "CAGR": compute_cagr(equity, ppy),
        "Sharpe": compute_sharpe(pnl, ppy),
        "MaxDD": max_drawdown(equity),
    }
    out = pd.DataFrame({"price": prices, "signal": pos, "ret": ret, "pnl": pnl, "equity": equity})
    return out, metrics
