import math

import pandas as pd

from quantboard.backtest import run_backtest


def test_backtest_produces_trades_and_metrics() -> None:
    index = pd.date_range("2024-01-01", periods=10, freq="D")
    close = pd.Series([100, 101, 102, 103, 102, 101, 100, 99, 100, 101], index=index, name="close")

    fast = close.rolling(2).mean()
    slow = close.rolling(3).mean()

    signals = pd.Series(0.0, index=index)
    crossover = fast > slow
    signals[crossover.fillna(False)] = 1.0
    signals[~crossover.fillna(False)] = 0.0

    bt, metrics = run_backtest(close.to_frame(), signals, interval="1d")

    assert set(metrics.keys()) == {
        "CAGR",
        "Sharpe",
        "Sortino",
        "Max Drawdown",
        "Win rate",
        "Avg trade return",
        "Exposure (%)",
        "Trades count",
    }

    assert metrics["Trades count"] > 0
    assert math.isfinite(metrics["Avg trade return"])
    assert len(bt) == len(close)
    assert bt["equity"].iloc[0] == 1.0
