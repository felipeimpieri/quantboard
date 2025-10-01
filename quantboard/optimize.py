import numpy as np
import pandas as pd
from .strategies import signals_sma_crossover
from .backtest import run_backtest

def grid_search_sma(
    close: pd.Series,
    fast_range: range,
    slow_range: range,
    fee_bps: int = 0,
    slippage_bps: int = 0,
    interval: str = "1d",
    metric: str = "Sharpe",
) -> pd.DataFrame:
    rows = []
    for f in fast_range:
        row = {}
        for s in slow_range:
            if f >= s:
                row[s] = np.nan
                continue
            sig, _ = signals_sma_crossover(close, fast=f, slow=s)
            bt, m = run_backtest(
                close.to_frame(name="close"),
                sig,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
                interval=interval,
            )
            row[s] = float(m.get(metric, float("nan")))
        rows.append(pd.Series(row, name=f))
    return pd.DataFrame(rows)

__all__ = ["grid_search_sma"]
