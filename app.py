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

# Now import and run the dashboard app
if __name__ == "__main__":
    # Import the actual dashboard app
    from dashboard.app import *

