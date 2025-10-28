"""Utilities to load and cache Lottie animation JSON assets."""
from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=32)
def load_lottie_json(relative_path: str) -> dict:
    """Load a Lottie JSON asset from the correct path."""
    # Get the current file's directory and navigate to assets
    current_file = Path(__file__).resolve()
    
    # Try multiple possible paths
    possible_paths = [
        # From utils/lottie_loader.py -> pharmgx-clinical-dashboard/assets/lottie/
        current_file.parents[2] / "assets" / "lottie" / relative_path,
        # Alternative: from utils/ -> src/pharmgx-clinical-dashboard/assets/lottie/
        current_file.parents[1] / "pharmgx-clinical-dashboard" / "assets" / "lottie" / relative_path,
        # Direct path from project root
        Path.cwd() / "src" / "pharmgx-clinical-dashboard" / "assets" / "lottie" / relative_path,
    ]
    
    for asset_path in possible_paths:
        if asset_path.exists():
            try:
                with open(asset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Validate it's a proper Lottie file
                    if isinstance(data, dict) and "layers" in data and "v" in data:
                        return data
            except Exception as e:
                print(f"Error loading {asset_path}: {e}")
                continue
    
    # If no valid file found, return empty dict
    return {}


