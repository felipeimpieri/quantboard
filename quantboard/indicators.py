import pandas as pd
import numpy as np

# --- Simple Moving Average ---
def sma(series: pd.Series, window: int = 20) -> pd.Series:
    return series.rolling(window).mean().rename(f"SMA_{window}")

# --- Relative Strength Index (Wilder) ---
def rsi(series: pd.Series, window: int | None = None, period: int = 14) -> pd.Series:
    win = window if window is not None else period
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1 / win, adjust=False).mean()
    roll_down = down.ewm(alpha=1 / win, adjust=False).mean()
    rs = roll_up / roll_down
    out = 100 - 100 / (1 + rs)
    return out.rename(f"RSI_{win}")

# --- Exponential Moving Average ---
def ema(series: pd.Series, window: int = 20) -> pd.Series:
    return series.ewm(span=window, adjust=False).mean().rename(f"EMA_{window}")

# --- MACD ---
def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"MACD": macd_line, "MACD_signal": signal_line, "MACD_hist": hist})

# --- Bollinger Bands ---
def bollinger(series: pd.Series, window: int = 20, n_std: float = 2.0) -> pd.DataFrame:
    mid = series.rolling(window).mean()
    std = series.rolling(window).std(ddof=0)
    upper = mid + n_std * std
    lower = mid - n_std * std
    return pd.DataFrame({"BB_mid": mid, "BB_upper": upper, "BB_lower": lower})

__all__ = ["sma", "rsi", "ema", "macd", "bollinger"]
