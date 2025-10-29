"""
Entry point for Streamlit Cloud deployment
Forwards to the main dashboard application
"""
import streamlit as st
import sys
from pathlib import Path

# --- Robust Path Setup for Deployment ---
# This is the single source of truth for path configuration.

# This file's location (/.../pharmgx-clinical-dashboard/app.py)
_APP_DIR = Path(__file__).resolve().parent

# The 'src' directory containing all modules (/.../pharmgx-clinical-dashboard/src)
_SRC_DIR = _APP_DIR / "src"

# The project root, one level above 'src'
_PROJECT_ROOT = _APP_DIR.parent

# Add all necessary paths to sys.path to ensure all imports work
sys.path.insert(0, str(_SRC_DIR))
sys.path.insert(1, str(_PROJECT_ROOT))

# Now import and run the dashboard app
if __name__ == "__main__":
    from dashboard.app import main
    main()
