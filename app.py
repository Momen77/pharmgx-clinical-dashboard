"""
Entry point for Streamlit Cloud deployment
Forwards to the main dashboard application
"""
import streamlit as st
import sys
from pathlib import Path

# Correctly resolve the 'src' directory.
# In Streamlit Cloud, this file is at /app/src/pharmgx-clinical-dashboard/app.py
# The target 'src' directory is at /app/src/pharmgx-clinical-dashboard/src
src_path = Path(__file__).resolve().parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Now import and run the dashboard app
if __name__ == "__main__":
    # Import the actual dashboard app
    from dashboard.app import *
