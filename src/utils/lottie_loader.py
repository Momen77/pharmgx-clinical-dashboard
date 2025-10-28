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
    
    # Debug: print paths being checked
    print(f"DEBUG: Looking for {relative_path}")
    for base in base_candidates:
        asset_path = base / "assets" / "lottie" / relative_path
        print(f"DEBUG: Checking {asset_path} - exists: {asset_path.exists()}")
        if asset_path.exists():
            try:
                with open(asset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # basic validation
                    if isinstance(data, dict) and data.get("layers") is not None:
                        print(f"DEBUG: Successfully loaded {relative_path}")
                        return data
                    else:
                        print(f"DEBUG: Invalid Lottie data in {relative_path}")
            except Exception as e:
                print(f"DEBUG: Error loading {relative_path}: {e}")
                pass
    
    print(f"DEBUG: Failed to load {relative_path}")
    return {}


