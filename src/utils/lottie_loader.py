"""Utilities to load and cache Lottie animation JSON assets."""
from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=32)
def load_lottie_json(relative_path: str) -> dict:
    """Load a Lottie JSON asset, trying multiple known locations."""
    base_candidates = [
        Path(__file__).resolve().parents[2],  # pharmgx-clinical-dashboard/
        Path(__file__).resolve().parents[3] / "src" / "pharmgx-clinical-dashboard",  # project-root/src/pharmgx-clinical-dashboard
    ]
    for base in base_candidates:
        asset_path = base / "assets" / "lottie" / relative_path
        if asset_path.exists():
            try:
                with open(asset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # basic validation
                    if isinstance(data, dict) and data.get("layers") is not None:
                        return data
            except Exception:
                pass
    return {}


