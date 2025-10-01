# Design Principles

## Naming
- Usar `snake_case` para funciones y variables; `PascalCase` para clases.
- Nombres descriptivos, evitar abreviaturas salvo siglas comunes (SMA, RSI, etc.).

## Typing
- Emplear *type hints* y `typing` para parámetros y retornos.
- Preferir `dataclass` o `pydantic` para estructuras de datos complejas.

## Data validation
- Validar entradas públicas (`ticker`, rangos, ventanas) y lanzar excepciones claras.
- Normalizar `DataFrame`/`Series` antes de procesar (índices, tipos numéricos).

## Error handling
- Capturar excepciones externas (API, red) y traducirlas a errores propios del dominio.
- Evitar silencios: registrar el error y devolver resultados vacíos solo si se justifica.

## Logging
- Usar el módulo estándar `logging` con niveles (`debug`, `info`, `warning`, `error`).
- Configurar un logger jerárquico (`quantboard.*`) y permitir ajuste de nivel desde la app.
