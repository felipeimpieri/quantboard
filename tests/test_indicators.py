import math

import pandas as pd
import pandas.testing as pdt

from quantboard.indicators import rsi, sma


def test_sma_window_three_matches_expected_mean() -> None:
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], name="close")
    result = sma(series, window=3)

    expected = pd.Series([float("nan"), float("nan"), 2.0, 3.0, 4.0], name="SMA_3")
    pdt.assert_series_equal(result, expected)


def test_rsi_matches_reference_value() -> None:
    prices = pd.Series(
        [
            44.34,
            44.09,
            44.15,
            43.61,
            44.33,
            44.83,
            45.10,
            45.42,
            45.84,
            46.08,
            45.89,
            46.03,
            45.61,
            46.28,
            46.28,
            46.00,
            46.03,
            46.41,
            46.22,
            45.64,
            46.21,
        ]
    )

    result = rsi(prices, period=14)

    assert math.isclose(result.iloc[13], 50.65741494172488, rel_tol=1e-12, abs_tol=1e-9)
    assert math.isclose(result.iloc[-1], 50.40461501951188, rel_tol=1e-12, abs_tol=1e-9)
    assert result.name == "RSI_14"
    assert len(result) == len(prices)
