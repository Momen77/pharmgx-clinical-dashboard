"""Utilities to load and cache Lottie animation JSON assets."""
from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=32)
def load_lottie_json(relative_path: str) -> dict:
    """Load a Lottie JSON asset from the correct path."""
    import os
    
    # Get the absolute path to the assets directory
    # This should work regardless of where the script is run from
    script_dir = Path(__file__).resolve().parent
    assets_dir = script_dir.parent.parent / "assets" / "lottie"
    asset_path = assets_dir / relative_path
    
    # Debug: show the path being checked
    print(f"Looking for: {relative_path}")
    print(f"Checking path: {asset_path}")
    print(f"Path exists: {asset_path.exists()}")
    
    if asset_path.exists():
        try:
            with open(asset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Validate it's a proper Lottie file
                if isinstance(data, dict) and "layers" in data and "v" in data:
                    print(f"Successfully loaded: {relative_path}")
                    return data
                else:
                    print(f"Invalid Lottie format in: {relative_path}")
        except Exception as e:
            print(f"Error loading {relative_path}: {e}")
    
    print(f"Failed to load: {relative_path}")
    return {}


