def interval_per_year(interval: str) -> int:
    # Aproximaciones razonables
    if interval == "1d":
        return 252
    if interval == "1h":
        return int(252 * 6.5)  # horas promedio por sesión en EEUU
    if interval == "1wk":
        return 52
    return 252
