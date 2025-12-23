"""Utilities for synchronizing URL query params with Streamlit session state."""

from typing import Any, Dict

import streamlit as st


def _coerce_type(value: Any, default: Any) -> Any:
    """Cast value to the type of default, falling back to default on failure."""
    if value is None:
        return default

    target_type = type(default)

    if isinstance(value, list):
        if not value:
            return default
        value = value[0]

    if target_type is type(None):
        return None

    if isinstance(value, target_type):
        return value

    try:
        if target_type is bool:
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes", "y", "on", "t"}:
                    return True
                if lowered in {"false", "0", "no", "n", "off", "f"}:
                    return False
            return bool(value)

        return target_type(value)
    except Exception:
        return default


def _get_query_params() -> Dict[str, Any]:
    """Return query params supporting both the new and experimental Streamlit APIs."""
    try:
        params = st.query_params
        if callable(getattr(params, "to_dict", None)):
            params = params.to_dict()
        else:
            params = dict(params)
        return {k: v for k, v in params.items()}
    except Exception:
        pass

    try:
        return st.experimental_get_query_params()
    except Exception:
        return {}


def _set_query_params(params: Dict[str, Any]) -> None:
    """Merge and set query params across the available Streamlit APIs."""
    current = _get_query_params()
    merged = {**current, **params}

    def _normalize(value: Any) -> Any:
        if isinstance(value, list):
            return [str(v) for v in value]
        if value is None:
            return ""
        return str(value)

    normalized = {k: _normalize(v) for k, v in merged.items()}

    try:
        st.query_params = normalized
        return
    except Exception:
        pass

    try:
        st.experimental_set_query_params(**normalized)
    except Exception:
        return


def get_param(key: str, default: Any) -> Any:
    """Fetch a parameter from the URL, falling back to session state or default."""
    params = _get_query_params()
    value = params.get(key)

    if value is None:
        if key in st.session_state:
            value = st.session_state[key]
        else:
            value = default

    coerced = _coerce_type(value, default)
    st.session_state[key] = coerced
    return coerced


def set_param(key: str, value: Any) -> None:
    """Update a parameter in session state and the URL query string."""
    st.session_state[key] = value
    _set_query_params({key: value})
