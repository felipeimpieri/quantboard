
# QuantBoard — Análisis técnico y Backtesting
Dashboard interactivo hecho con **Streamlit + yfinance + Plotly** para analizar precios, aplicar indicadores y correr backtests simples.

> **v0.2 – Novedades**
> - Indicadores: **SMA**, **EMA**, **RSI**, **Bollinger** (on/off desde la UI).
> - Estrategias de señales: **SMA crossover**, **RSI thresholds**, **Bollinger mean-reversion**, **Donchian breakout**.
> - Backtest con métricas: **CAGR**, **Sharpe**, **Max Drawdown**.
> - **Grid search** de SMA (heatmap) para explorar combinaciones *fast/slow*.
> - Aplicación dividida en páginas (`pages/`) para análisis y optimización.
> - Página **Watchlist** para seguir tickers y abrirlos en Home.
> - Página **SMA Heatmap** para probar rangos de SMA rápida/lenta y enviar el ticker al Home.
> - Página **Backtest SMA** con métricas, curva de equity y señales sobre el precio.
> - Limpieza de estructura de paquete (`quantboard/…`) y `.gitignore`.

---

## ¿Qué puedo hacer con QuantBoard?
- Ver el **gráfico de precio** (OHLC) con overlays de SMA/EMA/Bollinger y panel de **RSI**. Ahora también soporta datos intradiarios de 1 minuto con auto-refresco opcional.
- Generar **señales** con estrategias simples listas para usar.
- Correr un **backtest** rápido y ver métricas clave (CAGR, Sharpe, MaxDD).
- Visualizar **señales y curva de equity** del crossover de SMA en una página dedicada de backtesting.
- Explorar parámetros de SMA con un **heatmap** (grid search).
- Gestionar una **watchlist** con últimos precios y variación 30d.

---

## Requisitos
- **Python 3.10+**
- Dependencias en `requirements.txt`

---

## Cómo correrlo (Windows / macOS / Linux)
```bash
# 1) Clonar
git clone https://github.com/felipeimpieri/quantboard.git
cd quantboard

# 2) Crear y activar entorno
# Windows (PowerShell)
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# 3) Instalar dependencias e iniciar
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run streamlit_app.py
