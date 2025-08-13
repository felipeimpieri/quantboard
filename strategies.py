import pandas as pd
from .indicators import sma, rsi as rsi_ind

def signals_sma_crossover(close: pd.Series, fast: int = 20, slow: int = 50) -> pd.Series:
    """Señal long-only: 1 si SMA(fast) > SMA(slow), 0 si no. Sin shorts."""
    f = sma(close, fast)
    s = sma(close, slow)
    sig = (f > s).astype(int)
    return sig

def signals_rsi(close: pd.Series, length: int = 14, low: int = 30, high: int = 70) -> pd.Series:
    """
    Señal long-only: 1 cuando RSI < low (compra), 0 cuando RSI > high (salida).
    Mantiene posición hasta señal de salida.
    """
    r = rsi_ind(close, length)
    pos = pd.Series(0, index=close.index, dtype=int)
    holding = False
    for i in range(len(close)):
        if not holding and r.iat[i] < low:
            holding = True
        elif holding and r.iat[i] > high:
            holding = False
        pos.iat[i] = 1 if holding else 0
    return pos
