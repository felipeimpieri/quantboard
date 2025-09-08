# Refactor Plan

## Etapa 1 – Bajo riesgo
- Añadir *docstrings* y *type hints* consistentes en todos los módulos.
- Reemplazar `print`/`st.write` de depuración por `logging` y configurar nivel global.
- Cubrir utilidades (`utils`, `indicators`) con tests unitarios básicos.

## Etapa 2 – Riesgo medio
- Dividir cada módulo en subpaquetes como en el árbol propuesto (`data/`, `strategies/`, etc.).
- Centralizar la validación de parámetros usando `pydantic` o funciones dedicadas.
- Crear una API de backtest orientada a objetos para soportar múltiples estrategias.

## Etapa 3 – Alto impacto
- Integrar múltiples fuentes de datos (ej. Alpaca, CSV local) con interfaz común y caching.
- Implementar sistema de *plugins* para agregar estrategias e indicadores externos.
- Añadir motor de backtesting con soporte de carteras y manejo de riesgo.
