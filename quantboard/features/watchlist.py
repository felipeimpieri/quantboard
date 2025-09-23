from __future__ import annotations

"""Persistence helpers for the user watchlist."""

import json
from pathlib import Path
from typing import List

# Path to repo root so data/ works both in development and package install
BASE_DIR = Path(__file__).resolve().parent.parent.parent
WATCHLIST_PATH = BASE_DIR / "data" / "watchlist.json"


def load_watchlist() -> List[str]:
    """Load tickers from disk, returning an empty list if absent."""
    if WATCHLIST_PATH.exists():
        try:
            with WATCHLIST_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [str(t).upper() for t in data]
        except Exception:
            return []
    return []


def save_watchlist(tickers: List[str]) -> None:
    """Persist tickers to JSON, creating the folder if needed."""
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with WATCHLIST_PATH.open("w", encoding="utf-8") as f:
        json.dump(sorted(set(t.upper() for t in tickers)), f, ensure_ascii=False, indent=2)
