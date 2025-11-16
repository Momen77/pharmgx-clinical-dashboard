"""
Entry point for Streamlit Cloud deployment
Forwards to the main dashboard application
"""
import sys
from pathlib import Path
import runpy

# Add src to path for all imports
project_root = Path(__file__).resolve().parent
src_dir = project_root / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Run the dashboard app as a script (preserves proper module context)
dashboard_app_path = src_dir / "dashboard" / "app.py"
runpy.run_path(str(dashboard_app_path), run_name="__main__")

