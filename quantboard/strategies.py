import pandas as pd
from .indicators import sma, rsi, bollinger

def signals_sma_crossover(close: pd.Series, fast: int = 20, slow: int = 50, allow_short: bool = False):
    f = sma(close, fast)
    s = sma(close, slow)
    sig = pd.Series(0.0, index=close.index)
    if allow_short:
        cross_up = (f > s) & (f.shift(1) <= s.shift(1))
        cross_dn = (f < s) & (f.shift(1) >= s.shift(1))
        sig[cross_up] = 1
        sig[cross_dn] = -1
        sig = sig.replace(0, None).ffill().fillna(0.0)
    else:
        sig = (f > s).astype(float)
    sig.name = "signal"
    overlays = {"SMA_fast": f, "SMA_slow": s}
    return sig, overlays

def signals_rsi(close: pd.Series, period: int = 14, lower: int = 30, upper: int = 70):
    r = rsi(close, period)
    buy = (r.shift(1) < lower) & (r >= lower)
    sell = (r.shift(1) > upper) & (r <= upper)
    sig = pd.Series(0.0, index=close.index)
    sig[buy] = 1
    sig[sell] = 0
    sig = sig.replace(0, None).ffill().fillna(0.0)
    sig.name = "signal"
    return sig, {"RSI": r}

def signals_bollinger_mean_reversion(close: pd.Series, window: int = 20, n_std: float = 2.0):
    bb = bollinger(close, window, n_std)
    buy = (close.shift(1) < bb["BB_lower"].shift(1)) & (close >= bb["BB_lower"])
    sell = (close.shift(1) > bb["BB_upper"].shift(1)) & (close <= bb["BB_upper"])
    sig = pd.Series(0.0, index=close.index)
    sig[buy] = 1
    sig[sell] = 0
    sig = sig.replace(0, None).ffill().fillna(0.0)
    sig.name = "signal"
    return sig, {"BB": bb}

def signals_donchian_breakout(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20):
    upper = high.rolling(window).max()
    lower = low.rolling(window).min()
    sig = pd.Series(0.0, index=close.index)
    sig[close > upper.shift(1)] = 1
    sig[close < lower.shift(1)] = 0
    sig = sig.replace(0, None).ffill().fillna(0.0)
    sig.name = "signal"
    return sig, {"Donchian_upper": upper, "Donchian_lower": lower}

__all__ = [
    "signals_sma_crossover",
    "signals_rsi",
    "signals_bollinger_mean_reversion",
    "signals_donchian_breakout",
]
