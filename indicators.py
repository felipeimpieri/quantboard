import numpy as np
import pandas as pd

def sma(series: pd.Series, length: int = 20) -> pd.Series:
    return series.rolling(length, min_periods=length).mean()

def ema(series: pd.Series, length: int = 20) -> pd.Series:
    return series.ewm(span=length, adjust=False, min_periods=length).mean()

def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(gain, index=series.index).rolling(length).mean()
    roll_down = pd.Series(loss, index=series.index).rolling(length).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({
        "MACD": macd_line,
        "MACD_signal": signal_line,
        "MACD_hist": hist
    })
