import pandas as pd
import numpy as np
from .utils import interval_per_year

def run_backtest(df: pd.DataFrame, signals: pd.Series, fee_bps: int = 5, slippage_bps: int = 2, interval: str = "1d"):
    df = df.copy()
    df = df.loc[signals.index]
    df["signal"] = signals.astype(float).fillna(0.0)

    # Position state (carry yesterday's signal)
    df["position"] = df["signal"].shift(1).fillna(0.0)

    # Returns
    ret = df["Close"].pct_change().fillna(0.0)
    # Trading costs when position changes
    pos_change = df["position"].diff().abs().fillna(df["position"].abs())
    cost = pos_change * ((fee_bps + slippage_bps) / 10000.0)

    strat_ret = df["position"] * ret - cost
    equity = (1 + strat_ret).cumprod()

    # Trades
    entries = df.index[(pos_change > 0) & (df["position"] > 0)]
    exits = df.index[(pos_change > 0) & (df["position"] == 0)]
    trades = []
    open_price = None
    open_date = None
    for ts in df.index:
        if ts in entries and open_price is None:
            open_date = ts
            open_price = df.at[ts, "Close"]
        if ts in exits and open_price is not None:
            close_price = df.at[ts, "Close"]
            trades.append({
                "entry_date": open_date,
                "entry_price": float(open_price),
                "exit_date": ts,
                "exit_price": float(close_price),
                "return_pct": float((close_price / open_price) - 1.0)
            })
            open_price = None
            open_date = None
    trades_df = pd.DataFrame(trades)

    # Metrics
    periods = interval_per_year(interval)
    total_return = equity.iloc[-1] - 1.0 if not equity.empty else 0.0
    n = len(equity)
    cagr = (equity.iloc[-1]) ** (periods / max(n, 1)) - 1.0 if n > 0 else 0.0

    roll_max = equity.cummax() if not equity.empty else equity
    drawdown = (equity / roll_max) - 1.0 if not equity.empty else equity
    max_drawdown = float(drawdown.min()) if not equity.empty else 0.0

    vol = strat_ret.std() * np.sqrt(periods) if strat_ret.std() > 0 else np.nan
    sharpe = (strat_ret.mean() * periods) / vol if vol and not np.isnan(vol) else 0.0

    metrics = {
        "total_return": float(total_return),
        "cagr": float(cagr),
        "max_drawdown": float(max_drawdown),
        "sharpe": float(sharpe),
        "periods_per_year": periods,
        "periods": int(n),
    }

    results = pd.DataFrame({
        "equity": equity,
        "strategy_return": strat_ret
    })
    results_csv = results.to_csv(index=True)

    return {
        "equity": equity,
        "trades": trades_df,
        "metrics": metrics,
        "results_csv": results_csv
    }
