"""State helpers to sync Streamlit session state with query parameters."""
from __future__ import annotations

from datetime import date, datetime
from html import escape
from typing import Any, TypeVar, cast
from uuid import uuid4

import streamlit as st
from streamlit.components.v1 import html

T = TypeVar("T")


def _normalize_query_value(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _coerce_value(raw: Any, default: T) -> T:
    if raw is None:
        return default

    if isinstance(default, bool):
        if isinstance(raw, bool):
            return cast(T, raw)
        value = str(raw).strip().lower()
        if value in {"1", "true", "yes", "on"}:
            return cast(T, True)
        if value in {"0", "false", "no", "off"}:
            return cast(T, False)
        return default

    if isinstance(default, int) and not isinstance(default, bool):
        try:
            return cast(T, int(raw))
        except (TypeError, ValueError):
            return default

    if isinstance(default, float):
        try:
            return cast(T, float(raw))
        except (TypeError, ValueError):
            return default

    if isinstance(default, datetime):
        try:
            return cast(T, datetime.fromisoformat(str(raw)))
        except (TypeError, ValueError):
            return default

    if isinstance(default, date):
        try:
            return cast(T, date.fromisoformat(str(raw)))
        except (TypeError, ValueError):
            return default

    if isinstance(default, str):
        return cast(T, str(raw))

    return cast(T, raw)


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def get_param(key: str, default: T) -> T:
    """Return a value prioritising query params, then session_state, then default."""
    params = st.query_params
    if key in params:
        raw = _normalize_query_value(params.get(key))
        return _coerce_value(raw, default)

    if key in st.session_state:
        return cast(T, st.session_state[key])

    return default


def set_param(key: str, value: Any | None) -> None:
    """Persist *value* both in session_state and query params."""
    params = st.query_params

    if value is None:
        st.session_state.pop(key, None)
        if key in params:
            try:
                del params[key]
            except Exception:
                params[key] = ""
        return

    st.session_state[key] = value
    target = _stringify(value)
    current = _normalize_query_value(params.get(key)) if key in params else None
    if current != target:
        params[key] = target


def shareable_link_button(label: str = "Copy shareable link") -> None:
    """Render a small button that copies the current page URL to the clipboard."""
    button_id = f"copy-link-{uuid4().hex}"
    safe_label = escape(label)
    html(
        f"""
        <div style="display:flex;justify-content:flex-end;margin-bottom:0.5rem;">
            <button id="{button_id}" style="padding:0.35rem 0.8rem;border-radius:0.5rem;border:1px solid rgba(250,250,250,0.35);background:transparent;color:inherit;cursor:pointer;">
                {safe_label}
            </button>
        </div>
        <script>
            const btn = document.getElementById('{button_id}');
            if (btn) {{
                const originalText = btn.textContent;
                btn.addEventListener('click', async () => {{
                    try {{
                        await navigator.clipboard.writeText(window.parent.location.href);
                        btn.textContent = 'Copied!';
                    }} catch (err) {{
                        console.warn('Copy failed', err);
                        btn.textContent = 'Link ready';
                    }}
                    setTimeout(() => {{ btn.textContent = originalText; }}, 2000);
                }});
            }}
        </script>
        """,
        height=56,
    )
