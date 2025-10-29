"""
Entry point for Streamlit Cloud deployment
Forwards to the main dashboard application
"""
import streamlit as st
import sys
from pathlib import Path

# Add src to path for all imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))
# Correctly resolve the 'src' directory, which is the parent of this file's directory.
# This makes the entry point work for both local execution and cloud deployment.
project_root = Path(__file__).resolve().parent
src_dir = project_root / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Now import and run the dashboard app
if __name__ == "__main__":
    # Import the actual dashboard app
    from dashboard.app import *

