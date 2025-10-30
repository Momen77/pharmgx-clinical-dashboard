"""
Entry point for Streamlit Cloud deployment
Forwards to the main dashboard application
"""
import sys
from pathlib import Path

# Add src to path for all imports
project_root = Path(__file__).resolve().parent
src_dir = project_root / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import and execute the actual dashboard app
from src.dashboard.app import *

