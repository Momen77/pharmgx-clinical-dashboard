"""
Main Streamlit Dashboard Application
Clinical Pharmacogenomics Testing Dashboard - FULL APP RESTORED with robust imports
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import json

# =========================
# Robust import bootstrap
# =========================
# This section is removed. The entry point `pharmgx-clinical-dashboard/app.py`
# is now responsible for setting up the Python path correctly.
# Load PGxPipeline with multiple fallbacks
PGxPipeline = None
_import_errors = []
try:
    from src.main import PGxPipeline as _PG
    PGxPipeline = _PG
except Exception as e:
    _import_errors.append(f"src.main: {e}")
    try:
        from main import PGxPipeline as _PG
        PGxPipeline = _PG
    except Exception as e2:
        # Define these here for the dynamic import fallback
        _DASHBOARD_DIR = Path(__file__).resolve().parent
        _SRC_DIR = _DASHBOARD_DIR.parent

        _import_errors.append(f"main: {e2}")
        import importlib.util
        main_path = _SRC_DIR.parent / "main.py"
        if main_path.exists():
            spec = importlib.util.spec_from_file_location("main", main_path)
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)  # type: ignore
                PGxPipeline = getattr(mod, "PGxPipeline", None)
                if PGxPipeline is None:
                    _import_errors.append("dynamic: PGxPipeline not found in main.py")
            except Exception as e3:
                _import_errors.append(f"dynamic: {e3}")
        else:
            _import_errors.append(f"not found: {main_path}")

# =========================
# Dashboard module imports
# =========================
# Styling
try:
    from dashboard.utils.styling import inject_css
    _DASHBOARD_DIR = Path(__file__).resolve().parent
except Exception:
    try:
        from .utils.styling import inject_css  # type: ignore
    except Exception:
        def inject_css():
            st.markdown("<!-- Styling unavailable -->", unsafe_allow_html=True)

# Patient creator
try:
    from patient_creator import PatientCreator
except Exception:
    import importlib.util as _ilu
    _p = _DASHBOARD_DIR / "patient_creator.py"
    if _p.exists():
        _s = _ilu.spec_from_file_location("patient_creator", _p)
        _m = _ilu.module_from_spec(_s)
        _s.loader.exec_module(_m)  # type: ignore
        PatientCreator = getattr(_m, "PatientCreator", None)
    else:
        PatientCreator = None

# UI profile controls
try:
    from ui_profile import render_profile_controls, render_manual_enrichment_forms
except Exception:
    import importlib.util as _ilu
    _p = _DASHBOARD_DIR / "ui_profile.py"
    if _p.exists():
        _s = _ilu.spec_from_file_location("ui_profile", _p)
        _m = _ilu.module_from_spec(_s)
        _s.loader.exec_module(_m)  # type: ignore
        render_profile_controls = getattr(_m, "render_profile_controls", lambda: ("Manual (dashboard form)", "Auto (by age/lifestyle)"))
        render_manual_enrichment_forms = getattr(_m, "render_manual_enrichment_forms", lambda: ([], [], {}))
    else:
        render_profile_controls = lambda: ("Manual (dashboard form)", "Auto (by age/lifestyle)")
        render_manual_enrichment_forms = lambda: ([], [], {})

# Animation UI
try:
    from ui_animation import Storyboard, consume_events, create_storyboard_with_controls
except Exception:
    import importlib.util as _ilu
    _p = _DASHBOARD_DIR / "ui_animation.py"
    if _p.exists():
        _s = _ilu.spec_from_file_location("ui_animation", _p)
        _m = _ilu.module_from_spec(_s)
        _s.loader.exec_module(_m)  # type: ignore
        Storyboard = getattr(_m, "Storyboard", None)
        consume_events = getattr(_m, "consume_events", None)
        create_storyboard_with_controls = getattr(_m, "create_storyboard_with_controls", None)
    else:
        Storyboard = None
        consume_events = None
        create_storyboard_with_controls = None

# Gene panel
try:
    from gene_panel_selector import GenePanelSelector
except Exception:
    import importlib.util as _ilu
    _p = _DASHBOARD_DIR / "gene_panel_selector.py"
    if _p.exists():
        _s = _ilu.spec_from_file_location("gene_panel_selector", _p)
        _m = _ilu.module_from_spec(_s)
        _s.loader.exec_module(_m)  # type: ignore
        GenePanelSelector = getattr(_m, "GenePanelSelector", None)
    else:
        GenePanelSelector = None

# Worker & events
# Prefer the new PipelineWorker that passes dashboard profile correctly
try:
    from utils.pipeline_worker import PipelineWorker
except Exception:
    try:
        from utils.background_worker import EnhancedBackgroundWorker as PipelineWorker
    except Exception:
        PipelineWorker = None

try:
    from utils.event_bus import PipelineEvent
except Exception:
    PipelineEvent = None

# Visualization component
try:
    from components.jsonld_visualizer import (
        jsonld_to_hierarchy,
        render_d3_visualization,
        get_node_details,
    )
except Exception:
    jsonld_to_hierarchy = None
    render_d3_visualization = None
    get_node_details = None

# For handling clicks from the D3 component
import streamlit.components.v1 as components


def main():
    """Main function to run the Streamlit application."""

# =========================
# Streamlit page config
# =========================
st.set_page_config(
    page_title="UGent PGx Dashboard",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# Session state defaults
st.session_state.setdefault('patient_created', False)
st.session_state.setdefault('patient_profile', None)
st.session_state.setdefault('selected_genes', [])
st.session_state.setdefault('test_results', None)
st.session_state.setdefault('test_running', False)

# Sidebar nav
with st.sidebar:
    st.image("https://via.placeholder.com/200x60/1E64C8/FFFFFF?text=UGent+PGx", width=200)
    st.title("Navigation")
    page = st.radio(
        "Select Page",
        ["🏠 Home", "👤 Create Patient", "🧬 Select Genes", "🔬 Run Test", "📊 View Report", "💾 Export Data", "🛠️ Debug"],
        index=0,
    )

# =========================
# Pages
# =========================
    _DASHBOARD_DIR = Path(__file__).resolve().parent
    _SRC_DIR = _DASHBOARD_DIR.parent
    _PROJECT_ROOT = _SRC_DIR.parent

if page == "🏠 Home":
    st.title("🧬 UGent Pharmacogenomics Testing Dashboard")
    st.markdown("Welcome to the Clinical Pharmacogenomics Testing Platform")
    c1, c2, c3 = st.columns(3)
    c1.metric("Patients Tested", "1,234")
    c2.metric("Genes Analyzed", "25+")
    c3.metric("Drug Interactions", "500+")
    st.info("Use the sidebar to navigate the workflow")

elif page == "👤 Create Patient":
    st.title("👤 Create Patient")
    if PatientCreator is None:
        st.error("PatientCreator module not available")
    else:
        # Load config.yaml if available for API keys
        bioportal_key = None
        try:
            import yaml
            for cp in [
                _PROJECT_ROOT / "config.yaml",
                _SRC_DIR.parent / "config.yaml",
                _DASHBOARD_DIR.parent / "config.yaml",
                Path("config.yaml"),
            ]:
                if cp.exists():
                    with open(cp, 'r') as f:
                        cfg = yaml.safe_load(f)
                    bioportal_key = cfg.get('api', {}).get('bioportal_api_key')
                    break
        except Exception:
            pass
        creator = PatientCreator(bioportal_api_key=bioportal_key)
        profile = creator.render_patient_form()
        # PatientCreator should set st.session_state['patient_created'] and ['patient_profile']
        if st.session_state.get('patient_created'):
            st.success("✅ Patient profile created")
            with st.expander("Saved Profile", expanded=False):
                st.json(st.session_state.get('patient_profile', {}))

elif page == "🧬 Select Genes":
    st.title("🧬 Select Genes")
    if GenePanelSelector is None:
        st.error("GenePanelSelector module not available")
    else:
        selector = GenePanelSelector()
        selected = selector.render_gene_selector()
        if selected:
            st.session_state['selected_genes'] = selected
        st.info(f"Selected: {', '.join(st.session_state.get('selected_genes', [])) or 'None'}")

elif page == "🔬 Run Test":
    st.title("🔬 Run Pharmacogenetic Test")

    # Preconditions
    if not st.session_state.get('patient_created'):
        st.warning("Please create a patient profile first")
    if not st.session_state.get('selected_genes'):
        st.warning("Please select genes to test")

    if st.session_state.get('patient_created') and st.session_state.get('selected_genes'):
        demo_mode = st.checkbox("Demo mode (simulated pipeline)", value=True)

        mode, enrich = render_profile_controls()
        manual_conditions, manual_meds, manual_labs = [], [], {}
        if enrich == "Manual (enter now)":
            manual_conditions, manual_meds, manual_labs = render_manual_enrichment_forms()

        # Prepare profile copy to pass to worker
        profile = (st.session_state.get('patient_profile') or {}).copy()
        if enrich == "Auto (by age/lifestyle)":
            profile['auto_enrichment'] = True
        elif enrich == "Manual (enter now)":
            profile['manual_enrichment'] = {
                "conditions": manual_conditions,
                "medications": manual_meds,
                "labs": manual_labs,
            }
        
        # Remove non-serializable photo data before passing to worker
        if 'photo' in profile:
            del profile['photo']

        # Show passed profile for transparency
        with st.expander("Profile to pass", expanded=False):
            st.json(profile)

        # Create worker and storyboard
        if PipelineWorker is None or Storyboard is None or consume_events is None:
            st.error("Runtime modules missing (worker/animation)")
        else:
            import queue as _q
            import threading

            event_q = _q.Queue()
            result_q = _q.Queue()
            cancel_flag = threading.Event()

            # Resolve config
            config_path = "config.yaml"
            for cp in [
                _PROJECT_ROOT / "config.yaml",
                _SRC_DIR.parent / "config.yaml",
                _DASHBOARD_DIR.parent / "config.yaml",
                Path("config.yaml"),
            ]:
                if cp.exists():
                    config_path = str(cp)
                    break

            storyboard = Storyboard()
            st.info("Pipeline running... watch the animation above")

            worker = PipelineWorker(
                genes=st.session_state['selected_genes'],
                profile=profile,
                config_path=config_path,
                event_queue=event_q,
                result_queue=result_q,
                cancel_event=cancel_flag,
                demo_mode=demo_mode,
            )
            worker.start()

            cancel_col, status_col = st.columns([1, 3])
            with cancel_col:
                if st.button("Cancel Run", type="secondary"):
                    cancel_flag.set()
                    st.warning("Cancelling...")
            with status_col:
                consume_events(event_q, storyboard, worker_alive_fn=lambda: worker.is_alive())

            # Collect results
            results = result_q.get() if not result_q.empty() else {"success": False, "error": "No result"}
            if results.get('success'):
                st.session_state['test_results'] = results
                st.session_state['test_complete'] = True
                st.success("✅ Test Complete")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Variants Found", results.get('total_variants', 0))
                col2.metric("Genes Analyzed", len(results.get('genes', [])))
                col3.metric("Affected Drugs", results.get('affected_drugs', 0))
                col4.metric("Patient ID", results.get('patient_id', 'N/A'))

                # Show whether dashboard profile used
                cp = results.get('comprehensive_profile', {}) or {}
                used_dashboard = cp.get('dashboard_source', False)
                if used_dashboard:
                    st.success("✅ Used dashboard patient profile")
                else:
                    st.warning("⚠️ Used auto-generated profile")

                if 'comprehensive_outputs' in results and results['comprehensive_outputs']:
                    st.subheader("Generated Files")
                    for t, p in results['comprehensive_outputs'].items():
                        st.text(f"• {t}: {p}")
            else:
                st.error(f"Test failed: {results.get('error')}')")

elif page == "📊 View Report":
    st.title("📊 Clinical Report")
    results = st.session_state.get('test_results')
    if not results:
        st.warning("No results. Run a test first.")
    else:
        demo = (st.session_state.get('patient_profile') or {}).get('demographics', {})
        st.header("Patient Information")
        st.write(f"Name: {demo.get('first_name', '')} {demo.get('last_name', '')}")
        st.write(f"MRN: {demo.get('mrn', 'N/A')}")
        st.write(f"Age: {demo.get('age', 'N/A')}")

        st.header("Summary")
        st.write(f"Genes: {', '.join(results.get('genes', []))}")
        st.write(f"Total Variants: {results.get('total_variants', 0)}")

        cp = results.get('comprehensive_profile', {}) or {}
        st.write(f"Profile Source: {'Dashboard' if cp.get('dashboard_source') else 'Auto-generated'}")

        if 'comprehensive_outputs' in results:
            st.header("Generated Files")
            for t, p in results['comprehensive_outputs'].items():
                st.text(f"{t}: {p}")
        
        # Interactive Visualization Section
        st.header("Interactive Knowledge Graph")
        if render_d3_visualization is None:
            st.error("Visualization component is not available.")
        else:
            jsonld_path_str = (results.get('comprehensive_outputs', {}) or {}).get('JSON-LD')
            if jsonld_path_str and Path(jsonld_path_str).exists():
                with open(jsonld_path_str, 'r', encoding='utf-8') as f:
                    jsonld_data = json.load(f)

                with st.spinner("Generating interactive graph..."):
                    hierarchy_data = jsonld_to_hierarchy(jsonld_data)
                    if hierarchy_data:
                        render_d3_visualization(hierarchy_data)
                    else:
                        st.warning("Could not generate hierarchy from JSON-LD data.")

                # Handle clicks from the visualization
                clicked_node_uri = st.query_params.get("clicked_node_uri")
                if clicked_node_uri and get_node_details:
                    with st.expander(f"🔍 Details for: **{clicked_node_uri.split('/')[-1]}**", expanded=True):
                        details = get_node_details(jsonld_data, clicked_node_uri)
                        if not details:
                            st.write("No further details found for this node.")
                        else:
                            for prop, values in details.items():
                                st.markdown(f"**{prop}:**")
                                for value in values:
                                    if value.startswith("http"):
                                        st.markdown(f"- <{value}>")
                                    else:
                                        st.markdown(f"- {value}")
            else:
                st.warning("Comprehensive JSON-LD file not found. Cannot render visualization.")

elif page == "💾 Export Data":
    st.title("💾 Export Data")
    results = st.session_state.get('test_results')
    if not results:
        st.warning("No results to export")
    else:
        outputs = results.get('comprehensive_outputs', {})
        from pathlib import Path as _P
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Downloads")
            for label_key in [
                'Comprehensive JSON-LD',
                'Comprehensive TTL',
                'Comprehensive HTML Report',
                'Summary Report',
            ]:
                path = outputs.get(label_key)
                if path and _P(path).exists():
                    with open(path, 'rb') as fp:
                        st.download_button(f"Download {label_key}", fp.read(), file_name=_P(path).name)
        with col2:
            st.subheader("Paths")
            for t, p in outputs.items():
                exists = _P(p).exists() if p and isinstance(p, (str, _P)) else False
                st.text(f"{'✅' if exists else '❌'} {t}")
                st.code(p or '', language=None)

elif page == "🛠️ Debug":
    st.title("🛠️ Debug")
    st.header("Import Debug")
    st.write({
        "src_dir": str(_SRC_DIR),
        "project_root": str(_PROJECT_ROOT),
        "dashboard_dir": str(_DASHBOARD_DIR),
        "PGxPipeline_imported": PGxPipeline is not None,
        "import_errors": _import_errors,
    })
    st.subheader("sys.path (first 10)")
    st.code("\n".join(sys.path[:10]), language="text")

    st.header("Session State")
    st.json({k: v for k, v in st.session_state.items() if k in ['patient_created','patient_profile','selected_genes','test_results']})

    st.header("Animation Test")
    if create_storyboard_with_controls:
        try:
            debug_sb = create_storyboard_with_controls()
            st.success("Storyboard OK")
        except Exception as e:
            st.error(f"Storyboard error: {e}")
    else:
        st.info("Storyboard control helper not available")

else:
    st.error("Unknown page")

if __name__ == "__main__":
    # This allows running this file directly for local development
    main()
