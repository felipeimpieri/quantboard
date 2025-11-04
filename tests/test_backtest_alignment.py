import unittest

import numpy as np
import pandas as pd

from quantboard.backtest import run_backtest


def _compute_trade_returns(close: pd.Series, signals: pd.Series, shifted: bool) -> pd.Series:
    close = pd.to_numeric(close, errors="coerce").ffill()
    rets = close.pct_change().fillna(0.0)

    pos = pd.Series(signals, index=close.index, dtype=float)
    pos = pos.replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0).clip(-1, 1)

    strat_rets = pos.shift(1).fillna(0.0) * rets
    prev_pos = pos.shift(1).fillna(0.0)
    entries = (pos != 0.0) & (pos != prev_pos)

    trade_ids = entries.shift(1).cumsum() if shifted else entries.cumsum()
    trade_ids = trade_ids.where(pos != 0.0)

    grouped = (1.0 + strat_rets).groupby(trade_ids)
    trade_returns = grouped.prod() - 1.0
    return trade_returns.dropna()


class BacktestAlignmentTest(unittest.TestCase):
    def test_single_long_trade_alignment(self) -> None:
        index = pd.date_range("2023-01-01", periods=5, freq="D")
        close = pd.Series([100, 102, 105, 104, 104], index=index, dtype=float)
        signals = pd.Series([1, 1, 1, 1, 0], index=index, dtype=float)

        new_returns = _compute_trade_returns(close, signals, shifted=True)
        old_returns = _compute_trade_returns(close, signals, shifted=False)

        self.assertEqual(len(new_returns), 1)
        self.assertEqual(len(old_returns), 1)

        expected_return = (close.iloc[3] / close.iloc[0]) - 1.0
        self.assertAlmostEqual(new_returns.iloc[0], expected_return)
        self.assertAlmostEqual(old_returns.iloc[0], expected_return)

        _, metrics = run_backtest(close.to_frame(name="close"), signals)
        self.assertEqual(metrics["Trades count"], 1)
        self.assertAlmostEqual(metrics["Avg trade return"], expected_return)

    def test_flip_trade_keeps_flip_bar_with_prior_position(self) -> None:
        index = pd.date_range("2023-01-01", periods=5, freq="D")
        close = pd.Series([100, 102, 101, 99, 98], index=index, dtype=float)
        signals = pd.Series([1, 1, -1, -1, -1], index=index, dtype=float)

        new_returns = _compute_trade_returns(close, signals, shifted=True)
        old_returns = _compute_trade_returns(close, signals, shifted=False)

        self.assertEqual(len(new_returns), 2)
        self.assertEqual(len(old_returns), 2)

        rets = close.pct_change().fillna(0.0)
        expected_new = [
            (1.0 + rets.iloc[1]) * (1.0 + rets.iloc[2]) - 1.0,
            (1.0 - rets.iloc[3]) * (1.0 - rets.iloc[4]) - 1.0,
        ]
        expected_old = [
            (1.0 + rets.iloc[1]) - 1.0,
            (1.0 + rets.iloc[2]) * (1.0 - rets.iloc[3]) - 1.0,
        ]

        self.assertAlmostEqual(new_returns.iloc[0], expected_new[0])
        self.assertAlmostEqual(new_returns.iloc[1], expected_new[1])
        self.assertAlmostEqual(old_returns.iloc[0], expected_old[0])
        self.assertAlmostEqual(old_returns.iloc[1], expected_old[1])

        self.assertLess(new_returns.iloc[0], old_returns.iloc[0])
        self.assertGreater(new_returns.iloc[1], old_returns.iloc[1])

        _, metrics = run_backtest(close.to_frame(name="close"), signals)
        self.assertEqual(metrics["Trades count"], 2)
        self.assertAlmostEqual(
            metrics["Avg trade return"],
            float(np.mean(expected_new)),
        )


if __name__ == "__main__":
    unittest.main()
