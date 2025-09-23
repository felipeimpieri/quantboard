"""Heatmap helpers for SMA grid search."""

from __future__ import annotations

import pandas as pd

from .backtest import sma_crossover_metrics


def sma_grid_heatmap(
    close: pd.Series,
    fast_range: range,
    slow_range: range,
    metric: str = "CAGR",
) -> pd.DataFrame:
    """Calcula un DataFrame con el resultado de la métrica seleccionada.

    Los índices representan las ventanas de SMA rápida y las columnas las de
    SMA lenta. Para combinaciones inválidas (rápida >= lenta) se retorna ``NaN``.
    """

    rows: list[list[float]] = []
    fast_vals = list(fast_range)
    slow_vals = list(slow_range)

    for f in fast_vals:
        row: list[float] = []
        for s in slow_vals:
            if f >= s:
                row.append(float("nan"))
            else:
                m = sma_crossover_metrics(close, f, s)
                row.append(m.get(metric, float("nan")))
        rows.append(row)

    z = pd.DataFrame(rows, index=fast_vals, columns=slow_vals)
    z.index.name = "fast"
    z.columns.name = "slow"
    return z


__all__ = ["sma_grid_heatmap"]

