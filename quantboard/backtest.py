"""Backtesting utilities for QuantBoard."""

from __future__ import annotations

import pandas as pd

from .utils import periods_per_year, compute_cagr, compute_sharpe, max_drawdown
from .strategies import signals_sma_crossover


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
    """Backtest simple con señal 1/-1/0. Devuelve ``(result_df, metrics_dict)``."""

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
    out = pd.DataFrame(
        {"price": prices, "signal": pos, "ret": ret, "pnl": pnl, "equity": equity}
    )
    return out, metrics


def sma_crossover_metrics(
    close: pd.Series, fast: int, slow: int, interval: str = "1d"
) -> dict:
    """Ejecuta un backtest de SMA crossover y devuelve métricas.

    Parameters
    ----------
    close : pd.Series
        Serie de precios de cierre.
    fast : int
        Ventana de la SMA rápida.
    slow : int
        Ventana de la SMA lenta.
    interval : str
        Intervalo temporal (por defecto ``"1d"``).

    Returns
    -------
    dict
        Métricas calculadas (CAGR, Sharpe, MaxDD).
    """

    sig, _ = signals_sma_crossover(close, fast=fast, slow=slow)
    df = pd.DataFrame({"Close": close})
    _, metrics = run_backtest(df, sig, interval=interval)
    return metrics


__all__ = ["run_backtest", "sma_crossover_metrics"]

