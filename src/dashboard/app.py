"""
Main Streamlit Dashboard Application
Clinical Pharmacogenomics Testing Dashboard - FULL APP RESTORED with robust imports
"""
import streamlit as st
import json
import sys
from pathlib import Path
from datetime import datetime

# =========================
# Robust import bootstrap
# =========================
_DASHBOARD_DIR = Path(__file__).resolve().parent
_SRC_DIR = _DASHBOARD_DIR.parent
_PROJECT_ROOT = _SRC_DIR.parent

# Ensure src first for `from main` to work consistently
src_str = str(_SRC_DIR)
if src_str not in sys.path:
    sys.path.insert(0, src_str)
proj_str = str(_PROJECT_ROOT)
if proj_str not in sys.path:
    sys.path.insert(1, proj_str)
_dash_str = str(_DASHBOARD_DIR)
if _dash_str not in sys.path:
    sys.path.insert(2, _dash_str)

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
        _import_errors.append(f"main: {e2}")
        import importlib.util
        main_path = _SRC_DIR / "main.py"
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

# Worker & events with smart parameter handling
PipelineWorker = None
_worker_source = "none"

# Try importing workers in order of preference
try:
    from utils.pipeline_worker import PipelineWorker as _PW
    PipelineWorker = _PW
    _worker_source = "PipelineWorker"
except Exception as e1:
    try:
        from utils.background_worker import StreamlitCompatibleWorker as _PW
        PipelineWorker = _PW
        _worker_source = "StreamlitCompatibleWorker"
    except Exception as e2:
        try:
            from utils.background_worker import EnhancedBackgroundWorker as _PW
            # Wrap the old worker to handle new parameters
            import inspect
            import threading
            import queue as _queue_module
            
            class WorkerAdapter(threading.Thread):
                """Adapter to make old worker work with new interface"""
                def __init__(self, genes, patient_profile=None, profile=None, config_path="config.yaml", 
                             event_queue=None, result_queue=None, cancel_event=None, demo_mode=False):
                    super().__init__(daemon=True)
                    self.genes = genes
                    self.profile = patient_profile if patient_profile is not None else profile
                    self.event_queue = event_queue or _queue_module.Queue()
                    self.result_queue = result_queue or _queue_module.Queue()
                    self.cancel_event = cancel_event or threading.Event()
                    self.demo_mode = demo_mode
                    self.result = None
                    self.error = None
                    self.is_complete = False
                    
                    # Check what parameters the old worker accepts
                    try:
                        sig = inspect.signature(_PW.__init__)
                        self.old_worker_params = set(sig.parameters.keys())
                    except:
                        self.old_worker_params = {'genes', 'patient_profile'}
                
                def run(self):
                    try:
                        # Create worker with only the parameters it accepts
                        worker_kwargs = {}
                        if 'patient_profile' in self.old_worker_params:
                            worker_kwargs['patient_profile'] = self.profile
                        elif 'profile' in self.old_worker_params:
                            worker_kwargs['profile'] = self.profile
                        
                        worker = _PW(self.genes, **worker_kwargs)
                        
                        # Handle demo mode manually
                        if self.demo_mode:
                            import time
                            from utils.event_bus import PipelineEvent
                            stages = [
                                ("lab_prep", "DNA extraction & QC", 0.15),
                                ("ngs", "Sequencing & variant calling", 0.45),
                                ("annotation", "Clinical annotation & literature", 0.7),
                                ("enrichment", "Drug interactions & guidelines", 0.9),
                            ]
                            for s, msg, p in stages:
                                if self.cancel_event.is_set():
                                    break
                                self.event_queue.put(PipelineEvent(s, "processing", msg, p))
                                time.sleep(0.6)
                            
                            self.result = {
                                "success": True,
                                "genes": list(self.genes),
                                "patient_id": "DEMO",
                                "total_variants": 12,
                                "affected_drugs": 2,
                                "comprehensive_profile": {"patient_id": "DEMO", "dashboard_source": True},
                                "comprehensive_outputs": {"Comprehensive JSON-LD": "output/demo/DEMO_demo.jsonld"}
                            }
                        else:
                            # Run the old worker
                            worker.start()
                            worker.join()
                            self.result = worker.get_result() if hasattr(worker, 'get_result') else worker.result
                        
                        if self.result:
                            self.result_queue.put(self.result)
                    except Exception as e:
                        self.error = e
                        self.result_queue.put({"success": False, "error": str(e)})
                    finally:
                        self.is_complete = True
                
                def is_alive(self):
                    return super().is_alive() and not self.is_complete
            
            PipelineWorker = WorkerAdapter
            _worker_source = "EnhancedBackgroundWorker (adapted)"
        except Exception as e3:
            PipelineWorker = None
            _worker_source = f"none (errors: {e1}, {e2}, {e3})"

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
    st.image("https://via.placeholder.com/200x60/1E64C8/FFFFFF?text=UGent+PGx", width='stretch')
    st.title("Navigation")
    page = st.radio(
        "Select Page",
        ["🏠 Home", "👤 Create Patient", "🧬 Select Genes", "🔬 Run Test", "📊 View Report", "💾 Export Data", "🛠️ Debug"],
        index=0,
    )

# =========================
# Pages
# =========================
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

        # Show passed profile for transparency
        with st.expander("Profile to pass", expanded=False):
            st.json(profile)

        # Show test summary
        st.divider()
        st.subheader("Test Summary")
        summary_col1, summary_col2 = st.columns(2)
        with summary_col1:
            st.write(f"**Patient:** {profile.get('demographics', {}).get('first_name', 'N/A')} {profile.get('demographics', {}).get('last_name', 'N/A')}")
            st.write(f"**Genes to analyze:** {len(st.session_state['selected_genes'])}")
        with summary_col2:
            st.write(f"**Selected genes:** {', '.join(st.session_state['selected_genes'][:5])}{' ...' if len(st.session_state['selected_genes']) > 5 else ''}")
            st.write(f"**Estimated time:** ~2-5 minutes")
        
        # Add a button to start the test
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            run_test_button = st.button(
                "🧬 Run Pharmacogenetic Test",
                type="primary",
                width='stretch',
                key="run_test_main_button"
            )

        # Only run pipeline if button is clicked
        if run_test_button:
            if PGxPipeline is None:
                st.error("PGxPipeline not available - check imports")
                st.stop()
            
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

            # Debug info
            with st.expander("🔍 Debug Info", expanded=False):
                st.write(f"Genes: {st.session_state['selected_genes']}")
                st.write(f"Config path: {config_path}")
                st.write(f"Profile keys: {list(profile.keys())}")

            try:
                # Run pipeline with progress indicators
                st.info("🧬 Running pipeline...")
                
                # Show workflow stages as they would appear
                stages_display = st.container()
                with stages_display:
                    cols = st.columns(5)
                    stage_info = [
                        ("🧪", "Lab Prep", "DNA extraction"),
                        ("🧬", "Sequencing", "Variant calling"),
                        ("📝", "Annotation", "Clinical data"),
                        ("💊", "Drug Links", "Interactions"),
                        ("📊", "Report", "Final results")
                    ]
                    for col, (emoji, title, desc) in zip(cols, stage_info):
                        with col:
                            st.markdown(f"### {emoji}")
                            st.markdown(f"**{title}**")
                            st.caption(desc)
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Create event bus with callback to update progress
                from utils.event_bus import EventBus
                event_bus = EventBus()
                
                current_progress = [0]  # Use list to allow mutation in callback
                
                def update_progress(event):
                    stage_progress_map = {
                        "lab_prep": 0.2,
                        "ngs": 0.4,
                        "annotation": 0.6,
                        "enrichment": 0.8,
                        "linking": 0.85,
                        "report": 0.95,
                        "export": 1.0
                    }
                    
                    progress = stage_progress_map.get(event.stage, current_progress[0])
                    current_progress[0] = progress
                    progress_bar.progress(progress)
                    
                    message = getattr(event, 'message', f"Processing {event.stage}...")
                    status_text.text(f"⏳ {message}")
                
                event_bus.subscribe(update_progress)
                
                # Run pipeline with event bus
                pipeline = PGxPipeline(config_path=config_path, event_bus=event_bus)
                
                # Run multi-gene analysis
                results = pipeline.run_multi_gene(
                    gene_symbols=st.session_state['selected_genes'],
                    patient_profile=profile
                )
                
                # Complete progress
                progress_bar.progress(1.0)
                status_text.text("✅ Analysis complete!")
                
                # Show what we got
                with st.expander("🔍 Raw Results", expanded=False):
                    st.json(results)
            
            except Exception as e:
                st.error(f"❌ Pipeline failed: {e}")
                import traceback
                with st.expander("🐛 Error Details", expanded=True):
                    st.code(traceback.format_exc())
                results = {"success": False, "error": str(e)}
            
            # Process results
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
                st.error(f"❌ Test failed: {results.get('error', 'Unknown error')}")

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
                    with open(path, 'rb') as f:
                        st.download_button(f"Download {label_key}", f.read(), file_name=_P(path).name)
        with col2:
            st.subheader("Paths")
            for t, p in outputs.items():
                exists = _P(p).exists() if p else False
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
        "PipelineWorker_source": _worker_source,
        "PipelineWorker_available": PipelineWorker is not None,
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
