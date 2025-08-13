# QuantBoard — Análisis técnico y Backtesting (Streamlit + yfinance + Plotly)

Dashboard interactivo para analizar acciones con indicadores técnicos (SMA, RSI) y correr backtests simples de cruces de medias.  
Hecho en **Python + Streamlit + yfinance + Plotly**.

---

## ¿Qué hace?
- 📈 **Gráfico de precio** con **SMA rápida/lenta** y **RSI** (períodos configurables).
- 🧪 **Backtest** básico de **cruce de medias** (señales Buy/Sell y PnL simple).
- ⚙️ Parámetros ajustables (ticker, fechas, intervalo).
- 💻 UI 100% web con **Streamlit**.

---

## Requisitos
- Python **3.10+**
- Dependencias en `requirements.txt`

---

## Cómo correrlo (3 pasos)

```bash
# 1) Clonar
git clone https://github.com/felipeimpieri/quantboard.git
cd quantboard

# 2) Entorno e instalaciones
# Windows (PowerShell)
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

# 3) Iniciar
python -m streamlit run streamlit_app.py
