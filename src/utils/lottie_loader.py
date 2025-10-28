"""Utilities to load and cache Lottie animation JSON assets with robust path resolution."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional
import os


def load_lottie_json(relative_path: str) -> dict:
    """Load a Lottie JSON asset with multiple path resolution strategies."""
    
    # Strategy 1: Relative to current file (utils directory)
    script_dir = Path(__file__).resolve().parent
    assets_dir = script_dir.parent.parent / "assets" / "lottie"
    asset_path = assets_dir / relative_path
    
    # Strategy 2: Relative to project root
    if not asset_path.exists():
        # Try to find project root by looking for config.yaml
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "config.yaml").exists() or (parent / "requirements.txt").exists():
                assets_dir = parent / "assets" / "lottie"
                asset_path = assets_dir / relative_path
                break
    
    # Strategy 3: Absolute path from working directory
    if not asset_path.exists():
        cwd = Path.cwd()
        assets_dir = cwd / "assets" / "lottie"
        asset_path = assets_dir / relative_path
    
    # Strategy 4: Check if we're in a nested structure
    if not asset_path.exists():
        # Look for assets directory in parent directories
        current = Path(__file__).resolve()
        for parent in current.parents:
            potential_assets = parent / "assets" / "lottie"
            if potential_assets.exists():
                asset_path = potential_assets / relative_path
                break
    
    # Debug information
    print(f"[LOTTIE] Looking for: {relative_path}")
    print(f"[LOTTIE] Final path: {asset_path}")
    print(f"[LOTTIE] Path exists: {asset_path.exists()}")
    print(f"[LOTTIE] Working directory: {Path.cwd()}")
    
    if asset_path.exists():
        try:
            with open(asset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Validate it's a proper Lottie file
                if isinstance(data, dict) and ("layers" in data or "assets" in data) and "v" in data:
                    print(f"[LOTTIE] ✅ Successfully loaded: {relative_path}")
                    return data
                else:
                    print(f"[LOTTIE] ❌ Invalid Lottie format in: {relative_path}")
        except json.JSONDecodeError as e:
            print(f"[LOTTIE] ❌ JSON decode error in {relative_path}: {e}")
        except Exception as e:
            print(f"[LOTTIE] ❌ Error loading {relative_path}: {e}")
    
    print(f"[LOTTIE] ❌ Failed to load: {relative_path}, returning empty dict")
    return {}


def load_all_lottie_assets() -> Dict[str, dict]:
    """Load all Lottie assets and return a dictionary."""
    assets = {}
    asset_names = ["lab_prep.json", "ngs.json", "bioinformatics.json", "report.json", "placeholder.json"]
    
    for asset_name in asset_names:
        key = asset_name.replace(".json", "")
        assets[key] = load_lottie_json(asset_name)
    
    return assets


def get_asset_or_fallback(scene_name: str, assets: Dict[str, dict]) -> dict:
    """Get an asset or return placeholder/empty fallback."""
    if scene_name in assets and assets[scene_name]:
        return assets[scene_name]
    
    # Try placeholder
    if "placeholder" in assets and assets["placeholder"]:
        print(f"[LOTTIE] Using placeholder for {scene_name}")
        return assets["placeholder"]
    
    # Return minimal valid Lottie structure
    print(f"[LOTTIE] Using minimal fallback for {scene_name}")
    return {
        "v": "5.7.4",
        "fr": 24,
        "ip": 0,
        "op": 60,
        "w": 512,
        "h": 512,
        "nm": f"Fallback_{scene_name}",
        "ddd": 0,
        "assets": [],
        "layers": []
    }
