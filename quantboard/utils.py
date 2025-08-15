import numpy as np
import pandas as pd

_PERIODS_PER_YEAR = {"1d": 252, "1wk": 52, "1mo": 12}

def periods_per_year(interval: str) -> int:
    return _PERIODS_PER_YEAR.get(interval, 252)

def compute_cagr(equity: pd.Series, ppy: int = 252) -> float:
    n = len(equity)
    if n <= 1:
        return 0.0
    total = float(equity.iloc[-1]) / float(equity.iloc[0])
    years = n / ppy
    if years <= 0:
        return 0.0
    return total ** (1 / years) - 1

def compute_sharpe(returns: pd.Series, ppy: int = 252, rf: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    mu = float(returns.mean())
    sigma = float(returns.std(ddof=0))
    if sigma == 0:
        return 0.0
    return (mu - rf / ppy) / sigma * np.sqrt(ppy)

def max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    dd = equity / roll_max - 1.0
    return float(dd.min())
