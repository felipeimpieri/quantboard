from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class BTResult:
    equity: pd.Series
    returns: pd.Series


def _periods_per_year(interval: str) -> float:
    interval = (interval or "").lower()
    if interval == "1d":
        return 252.0
    if interval == "1wk":
        return 52.0
    if interval == "1mo":
        return 12.0
    if interval == "1h":
        return 252.0 * 6.5  # ~horas de mercado por año
    if interval == "1m":
        return 252.0 * 390.0  # ~minutos de mercado por año
    return 252.0


def _max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    dd = equity / roll_max - 1.0
    return float(dd.min()) if len(dd) else 0.0


def _cagr(equity: pd.Series, periods_per_year: float) -> float:
    if equity.empty:
        return 0.0
    n_periods = float(len(equity))
    years = n_periods / periods_per_year if periods_per_year > 0 else 1.0
    endv = float(equity.iloc[-1])
    return (endv ** (1.0 / years) - 1.0) if years > 0 and endv > 0 else 0.0


def _sharpe(rets: pd.Series, periods_per_year: float) -> float:
    if len(rets) == 0:
        return 0.0
    std = rets.std(ddof=0)
    if std == 0:
        return 0.0
    return float(rets.mean() / std * np.sqrt(periods_per_year))


def _sortino(rets: pd.Series, periods_per_year: float) -> float:
    if len(rets) == 0:
        return 0.0
    downside = rets[rets < 0]
    if len(downside) == 0:
        return 0.0
    downside_std = downside.std(ddof=0)
    if downside_std == 0:
        return 0.0
    return float(rets.mean() / downside_std * np.sqrt(periods_per_year))


def run_backtest(
    df: pd.DataFrame | pd.Series,
    signals: pd.Series,
    *,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
    interval: str = "1d",
) -> tuple[pd.DataFrame, dict]:
    """
    Backtest long/short con señales en {-1, 0, 1}.
    Costos aplicados en cada cambio de posición (fee + slippage en bps).
    Devuelve DataFrame con 'equity' y dict de métricas:
    CAGR, Sharpe, Sortino, Max Drawdown, Win rate, Avg trade return, Exposure y Trades.
    """
    if isinstance(df, pd.Series):
        close = pd.to_numeric(df, errors="coerce").fillna(method="ffill")
        data = close.to_frame(name="close")
    else:
        data = df.copy()
        data.columns = [str(c).lower() for c in data.columns]
        for c in ("open", "high", "low", "close"):
            if c not in data.columns and "close" in data.columns:
                data[c] = pd.to_numeric(data["close"], errors="coerce")
        close = pd.to_numeric(data.get("close"), errors="coerce").fillna(method="ffill")
    rets = close.pct_change().fillna(0.0)

    pos = pd.Series(signals, index=close.index).replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)
    pos = pos.clip(-1, 1)

    # Costos por cambio de posición
    turn = pos.diff().abs().fillna(0.0)  # 0->1, 1->-1, etc.
    total_cost_bps = float(fee_bps) + float(slippage_bps)
    cost = turn * (total_cost_bps / 10000.0)

    strat_rets = pos.shift(1).fillna(0.0) * rets - cost
    equity = (1.0 + strat_rets).cumprod()
    res_df = pd.DataFrame({"equity": equity, "returns": strat_rets})

    ppy = _periods_per_year(interval)
    sortino = _sortino(strat_rets, ppy)
    sharpe = _sharpe(strat_rets, ppy)
    cagr = _cagr(equity, ppy)
    max_dd = _max_drawdown(equity)

    prev_pos = pos.shift(1).fillna(0.0)
    entries = (pos != 0.0) & (pos != prev_pos)
    trade_ids = entries.cumsum()
    trade_ids = trade_ids.where(pos != 0.0)
    grouped = (1.0 + strat_rets).groupby(trade_ids)
    trade_returns = grouped.prod() - 1.0
    trade_returns = trade_returns.dropna()

    trades_count = int(trade_returns.count())
    win_rate = float((trade_returns > 0).mean()) if trades_count else 0.0
    avg_trade_return = float(trade_returns.mean()) if trades_count else 0.0
    exposure = float((pos != 0.0).mean()) if len(pos) else 0.0

    metrics = {
        "CAGR": cagr,
        "Sharpe": sharpe,
        "Sortino": sortino,
        "Max Drawdown": max_dd,
        "Win rate": win_rate,
        "Avg trade return": avg_trade_return,
        "Exposure (%)": exposure,
        "Trades count": trades_count,
    }
    return res_df, metrics
