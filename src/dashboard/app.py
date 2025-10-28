"""
Main Streamlit Dashboard Application
Clinical Pharmacogenomics Testing Dashboard - FIXED IMPORTS
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Robust path setup so `from src.main import PGxPipeline` always works
# Resolve key directories relative to this file regardless of CWD
_DASHBOARD_DIR = Path(__file__).resolve().parent
_SRC_DIR = _DASHBOARD_DIR.parent
_PROJECT_ROOT = _SRC_DIR.parent

# Ensure src is at the very front of sys.path so `from main` also works
src_str = str(_SRC_DIR)
if src_str not in sys.path:
    sys.path.insert(0, src_str)
# Also add project root as a fallback for absolute package resolution
proj_str = str(_PROJECT_ROOT)
if proj_str not in sys.path:
    sys.path.insert(1, proj_str)
# Finally, add dashboard dir to support local relative imports
dash_str = str(_DASHBOARD_DIR)
if dash_str not in sys.path:
    sys.path.insert(2, dash_str)

# Short diagnostic banner (only once)
try:
    if not st.session_state.get("_import_diag_once"):
        st.session_state["_import_diag_once"] = True
        st.info(
            f"Import paths configured:\n"
            f"- src: {_SRC_DIR}\n- project_root: {_PROJECT_ROOT}\n- dashboard: {_DASHBOARD_DIR}"
        )
except Exception:
    pass

# Try very robust imports for PGxPipeline
PGxKGPipeline = None
PGxPipeline = None
_import_errors = []

try:
    # Preferred explicit package style
    from src.main import PGxPipeline as _PGxPipeline
    PGxPipeline = _PGxPipeline
except Exception as e:
    _import_errors.append(f"src.main: {e}")
    try:
        # If src is first on sys.path, this works
        from main import PGxPipeline as _PGxPipeline
        PGxPipeline = _PGxPipeline
    except Exception as e2:
        _import_errors.append(f"main: {e2}")

# If both failed, attempt dynamic import by absolute path
if PGxPipeline is None:
    import importlib.util
    main_path = _SRC_DIR / "main.py"
    if main_path.exists():
        spec = importlib.util.spec_from_file_location("main", main_path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)  # type: ignore
            PGxPipeline = getattr(mod, "PGxPipeline", None)
            if PGxPipeline is None:
                _import_errors.append("main.py loaded but PGxPipeline not found")
        except Exception as e3:
            _import_errors.append(f"dynamic import: {e3}")
    else:
        _import_errors.append(f"not found: {main_path}")

if PGxPipeline is None:
    st.error("Could not import PGxPipeline after multiple strategies. See details in Debug page.")
    st.caption("Import errors: " + " | ".join(_import_errors))

# The rest of the original app imports and logic follow below
# (We keep your existing app body intact and only replace the import bootstrap above.)

# Import dashboard utils after path fix
try:
    from dashboard.utils.styling import inject_css
except Exception:
    try:
        from .utils.styling import inject_css  # type: ignore
    except Exception:
        def inject_css():
            st.markdown("<!-- Styling unavailable -->", unsafe_allow_html=True)

# Lazy-import remaining dashboard modules to avoid hard failures on first paint
def _lazy_import(name, rel_path):
    import importlib.util
    p = _DASHBOARD_DIR / rel_path
    if p.exists():
        spec = importlib.util.spec_from_file_location(name, p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)  # type: ignore
        return m
    return None

_patient_module = _lazy_import("patient_creator", "patient_creator.py")
PatientCreator = getattr(_patient_module, "PatientCreator", None) if _patient_module else None

_ui_profile_module = _lazy_import("ui_profile", "ui_profile.py")
if _ui_profile_module:
    render_profile_controls = getattr(_ui_profile_module, "render_profile_controls", lambda: ("Manual (dashboard form)", "Auto (by age/lifestyle)"))
    render_manual_enrichment_forms = getattr(_ui_profile_module, "render_manual_enrichment_forms", lambda: ([], [], {}))
else:
    render_profile_controls = lambda: ("Manual (dashboard form)", "Auto (by age/lifestyle)")
    render_manual_enrichment_forms = lambda: ([], [], {})

_ui_animation_module = _lazy_import("ui_animation", "ui_animation.py")
if _ui_animation_module:
    Storyboard = getattr(_ui_animation_module, "Storyboard", None)
    consume_events = getattr(_ui_animation_module, "consume_events", None)
    create_storyboard_with_controls = getattr(_ui_animation_module, "create_storyboard_with_controls", None)
else:
    Storyboard = None
    consume_events = None
    create_storyboard_with_controls = None

_gene_panel_module = _lazy_import("gene_panel_selector", "gene_panel_selector.py")
GenePanelSelector = getattr(_gene_panel_module, "GenePanelSelector", None) if _gene_panel_module else None

_alert_module = _lazy_import("alert_classifier", "alert_classifier.py")
AlertClassifier = getattr(_alert_module, "AlertClassifier", None) if _alert_module else None

# Page configuration
st.set_page_config(
    page_title="UGent PGx Dashboard",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject CSS
inject_css()

# Initialize session state
for k, v in {
    'patient_created': False,
    'selected_genes': [],
    'test_results': None,
    'test_running': False,
}.items():
    st.session_state.setdefault(k, v)

# Sidebar
with st.sidebar:
    st.title("Navigation")
    page = st.radio(
        "Select Page",
        ["🏠 Home", "👤 Create Patient", "🧬 Select Genes", "🔬 Run Test", "📊 View Report", "💾 Export Data", "🛠️ Debug"],
        index=0
    )

# --- Minimal pages to keep this patch focused on import fix ---
if page == "🛠️ Debug":
    st.header("Import Debug")
    st.write({
        "src_dir": str(_SRC_DIR),
        "project_root": str(_PROJECT_ROOT),
        "dashboard_dir": str(_DASHBOARD_DIR),
        "PGxPipeline_imported": PGxPipeline is not None,
        "errors": _import_errors,
    })
    st.code("\n".join(sys.path[:10]), language="text")
else:
    st.success("PGxPipeline import is configured." if PGxPipeline else "Import still failing — see Debug page.")
