# QuantBoard — Dashboard y Backtester en Python

**QuantBoard** es una app en **Streamlit** para análisis técnico rápido y **backtesting** simple de acciones usando datos de **yfinance**.


## Características
- ✅ Descarga de datos (yfinance) con caché
- ✅ Indicadores: SMA/EMA/RSI/MACD
- ✅ Estrategias incluidas: **Cruce de Medias** y **RSI** (long-only)
- ✅ Backtester vectorizado con métricas (Return, CAGR, Max Drawdown, Sharpe)
- ✅ Gráficos interactivos (**Plotly**) y descarga de CSV/Trades
- ✅ Interfaz web (**Streamlit**) + **CLI** (`python cli.py ...`)
- ✅ Tests y CI listos para GitHub Actions

## Requisitos
- Python 3.10+
- Instala dependencias:
  ```bash
  pip install -r requirements.txt
  ```

## Ejecutar la app
```bash
streamlit run streamlit_app.py
```

## Ejecutar un backtest por CLI
```bash
python cli.py --ticker AAPL --start 2023-01-01 --strategy sma --fast 10 --slow 30
```

## Estructura
```
quantboard/
  ├─ quantboard/
  │   ├─ __init__.py
  │   ├─ data.py
  │   ├─ indicators.py
  │   ├─ strategies.py
  │   ├─ backtest.py
  │   ├─ plots.py
  │   └─ utils.py
  ├─ streamlit_app.py
  ├─ cli.py
  ├─ requirements.txt
  ├─ tests/
  │   └─ test_indicators.py
  └─ .github/workflows/python.yml
```

## Roadmap (ideas para seguir creciendo)
- Multi-asset & portfolios (equity, crypto, ETFs)
- Órdenes con stop/TP, comisiones avanzadas, shorts
- Factores (value, momentum), walk-forward, optimizadores
- Exportar a HTML/PDF directo desde la app

---

Hecho con ❤️ en Python. Si te sirve, una ⭐ en GitHub ayuda.
