"""Utilities to load and cache Lottie animation JSON assets."""
from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=32)
def load_lottie_json(relative_path: str) -> dict:
    asset_path = Path(__file__).resolve().parents[2] / "assets" / "lottie" / relative_path
    if not asset_path.exists():
        return {}
    with open(asset_path, "r", encoding="utf-8") as f:
        return json.load(f)


