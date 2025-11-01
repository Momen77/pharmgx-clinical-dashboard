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

# Note: ui_profile imports removed - profile creation UI should not appear on Run Test page

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

                        # Pass through additional parameters if the worker accepts them
                        if 'config_path' in self.old_worker_params:
                            worker_kwargs['config_path'] = "config.yaml"
                        if 'event_queue' in self.old_worker_params:
                            worker_kwargs['event_queue'] = self.event_queue
                        if 'result_queue' in self.old_worker_params:
                            worker_kwargs['result_queue'] = self.result_queue
                        if 'cancel_event' in self.old_worker_params:
                            worker_kwargs['cancel_event'] = self.cancel_event
                        if 'demo_mode' in self.old_worker_params:
                            worker_kwargs['demo_mode'] = self.demo_mode

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

# Visualization component - try new module first, then fallback
try:
    from components.visualize_jsonld import (
        jsonld_to_hierarchy,
        render_d3_visualization,
        get_node_details,
    )
except Exception:
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
    # Display official UGent logo - smaller and left-aligned
    import os

    # Add spacing before logo
    st.markdown("<br>", unsafe_allow_html=True)

    # Try official main logo first, then SVG fallback
    main_logo_path = os.path.join(_PROJECT_ROOT, "assets", "ugent_main_logo.png")
    svg_logo_path = os.path.join(_PROJECT_ROOT, "assets", "ugent_logo.svg")

    # Left-aligned logo with moderate width
    if os.path.exists(main_logo_path):
        # Official UGent main logo
        st.image(main_logo_path, width=160)
    elif os.path.exists(svg_logo_path):
        # Custom SVG logo
        st.image(svg_logo_path, width=160)
    else:
        # Fallback: Use embedded SVG with transparent background
        logo_svg = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100" width="160" style="background: transparent;">
          <rect x="0" y="0" width="10" height="100" fill="#FFD200"/>
          <text x="25" y="60" font-family="Arial, Helvetica, sans-serif" font-size="28" font-weight="bold" fill="#1E64C8">
            GHENT UNIVERSITY
          </text>
        </svg>
        """
        st.markdown(logo_svg, unsafe_allow_html=True)

    st.divider()
    st.title("Workflow")
    
    # Show workflow steps with status indicators
    steps = [
        ("🏠 Home", True),
        ("👤 Create Patient", st.session_state.get('patient_created', False)),
        ("🧬 Select Genes", len(st.session_state.get('selected_genes', [])) > 0),
        ("🔬 Run Test", st.session_state.get('test_complete', False)),
        ("📊 View Results", st.session_state.get('test_complete', False)),
        ("💾 Export Data", st.session_state.get('test_complete', False))
    ]
    
    st.markdown("### Navigation")
    page_options = [step[0] for step in steps]
    page = st.radio(
        "Select Page",
        page_options + ["🛠️ Debug"],
        index=0,
        label_visibility="collapsed"
    )
    
    st.divider()
    st.markdown("### Progress")
    for step_name, completed in steps[1:]:  # Skip Home
        icon = "✅" if completed else "⏹️"
        st.caption(f"{icon} {step_name}")

# =========================
# Pages
# =========================
if page == "🏠 Home":
    st.title("🧬 Pharmacogenomics Testing Dashboard")
    st.markdown("### Welcome to the Clinical Pharmacogenomics Testing Platform")

    c1, c2, c3 = st.columns(3)
    c1.metric("Patients Tested", "1,234")
    c2.metric("Genes Analyzed", "25+")
    c3.metric("Drug Interactions", "500+")

    st.info("Use the sidebar to navigate the workflow")

elif page == "👤 Create Patient":
    st.title("👤 Create Patient")
    st.info("**Step 1:** Create a patient profile with demographics and clinical data. The profile will be auto-enhanced with diseases and medications.")

    if PatientCreator is None:
        st.error("PatientCreator module not available")
    else:
        # Profile creation mode selection
        st.subheader("Patient Profile Source")
        profile_mode = st.radio(
            "Choose how to create the patient profile:",
            ["Manual (Fill form)", "Auto-generate"],
            index=0,
            horizontal=True,
            help="Manual: Fill out the detailed patient form | Auto-generate: Create a random patient for testing"
        )

        st.divider()

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

        # Show form only if Manual mode is selected
        if profile_mode == "Manual (Fill form)":
            profile = creator.render_patient_form()
        else:
            # Auto-generate mode
            st.info("🤖 **Auto-generate mode:** A random patient profile will be created automatically with realistic demographics and clinical data.")

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🎲 Generate Random Patient Profile", type="primary", use_container_width=True):
                    profile = creator.generate_random_profile(generate_ai_photo=True)
                    if profile:
                        st.session_state['patient_profile'] = profile
                        st.session_state['patient_created'] = True

                        # Show generated profile
                        demo = profile.get('demographics', {})
                        st.success(f"✅ Random patient profile generated!")
                        st.info(f"**Generated Patient:** {demo.get('first_name', 'Unknown')} {demo.get('last_name', 'Unknown')} (MRN: {demo.get('mrn', 'N/A')})")

                        # Show AI-generated photo if available
                        if profile.get('photo') and profile.get('photo_format') == 'ai_generated':
                            st.image(profile['photo'], width=200, caption="✨ AI-Generated Patient Photo")
                        elif profile.get('photo'):
                            st.image(profile['photo'], width=200, caption="👤 Placeholder Avatar")
                            if profile.get('photo_format') == 'avatar':
                                st.caption("ℹ️ Check warnings above for AI photo generation status")

        # Show success message if profile was created
        if st.session_state.get('patient_created'):
            st.success("✅ Patient profile created and ready!")
            st.info("➡️ **Next:** Go to **🧬 Select Genes** to choose which genes to analyze.")
            with st.expander("📋 View Saved Profile", expanded=False):
                st.json(st.session_state.get('patient_profile', {}))

elif page == "🧬 Select Genes":
    st.title("🧬 Select Genes")
    st.info("**Step 2:** Select which pharmacogenomic genes to analyze for variants that may affect drug response.")
    
    # Check prerequisite
    if not st.session_state.get('patient_created'):
        st.warning("⚠️ Please create a patient profile first (Step 1)")
        st.stop()
    
    if GenePanelSelector is None:
        st.error("GenePanelSelector module not available")
    else:
        selector = GenePanelSelector()
        selected = selector.render_gene_selector()
        if selected:
            st.session_state['selected_genes'] = selected
        
        if st.session_state.get('selected_genes'):
            st.success(f"✅ Selected: {', '.join(st.session_state.get('selected_genes', []))}")
            st.info("➡️ **Next:** Go to **🔬 Run Test** to analyze these genes.")
        else:
            st.info(f"Selected: {', '.join(st.session_state.get('selected_genes', [])) or 'None'}")

elif page == "🔬 Run Test":
    st.title("🔬 Run Pharmacogenetic Test")
    st.info("**Step 3:** Run the comprehensive pharmacogenomic analysis pipeline on your selected genes.")

    # Preconditions
    if not st.session_state.get('patient_created'):
        st.warning("⚠️ Please create a patient profile first (Step 1)")
        st.stop()
    if not st.session_state.get('selected_genes'):
        st.warning("⚠️ Please select genes to test (Step 2)")
        st.stop()

    if st.session_state.get('patient_created') and st.session_state.get('selected_genes'):
        # Get profile from session state
        profile = (st.session_state.get('patient_profile') or {}).copy()

        # Extract patient demographics for display
        # Use top-level demographics shortcut (added for compatibility)
        demo = profile.get('demographics', {})
        first_name = demo.get('first_name', 'N/A')
        last_name = demo.get('last_name', 'N/A')
        mrn = demo.get('mrn', 'N/A')

        # Add a button to start the test
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            run_test_button = st.button(
                "🧬 Run Pharmacogenetic Test",
                type="primary",
                width='stretch',
                key="run_test_main_button"
            )

        # Set session state when button is clicked to hide test summary
        if run_test_button:
            st.session_state['test_started'] = True

        # Only show test summary if test hasn't started
        if not st.session_state.get('test_started', False):
            # Show test summary
            st.subheader("Test Summary")

            # Create layout with patient photo and summary info
            photo_col, summary_info_col = st.columns([1, 3])

            # Display patient photo
            with photo_col:
                if profile.get('photo'):
                    st.image(profile['photo'], width=150, caption="Patient Photo")
                else:
                    st.info("No photo available")

            # Display summary information
            with summary_info_col:
                summary_col1, summary_col2 = st.columns(2)
                with summary_col1:
                    st.write(f"**Patient:** {first_name} {last_name}")
                    st.write(f"**MRN:** {mrn}")
                    st.write(f"**Genes to analyze:** {len(st.session_state['selected_genes'])}")
                with summary_col2:
                    st.write(f"**Selected genes:** {', '.join(st.session_state['selected_genes'][:5])}{' ...' if len(st.session_state['selected_genes']) > 5 else ''}")
                    st.write(f"**Estimated time:** ~2-5 minutes")

            # Optional: Show patient profile details
            with st.expander("👤 View Patient Profile Details", expanded=False):
                st.json(profile)

            st.divider()

        # Only run pipeline if button is clicked
        if run_test_button:
            if PGxPipeline is None:
                st.error("PGxPipeline not available - check imports")
                if _import_errors:
                    with st.expander("🔎 Import errors", expanded=True):
                        for err in _import_errors:
                            st.code(str(err))
                # Abort running the pipeline if imports failed
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
                # Run pipeline (storyboard handles visual stages and status)
                
                # Deprecated: old Streamlit progress UI (replaced by storyboard progress)
                progress_bar = None
                status_text = None
                substep_text = None  # Deprecated: storyboard handles sub-steps

                # ==============================================
                # THREAD-SAFE QUEUE-BASED EVENT HANDLING
                # ==============================================
                # Use queue to avoid ScriptRunContext errors when
                # worker threads emit events
                import queue
                import threading
                import time

                event_queue = queue.Queue()
                result_queue = queue.Queue()
                cancel_event = threading.Event()

                current_progress = [0]  # Use list to allow mutation

                # Define detailed sub-steps for each stage
                stage_substeps = {
                    "lab_prep": [
                        "Preparing sample...",
                        "DNA extraction in progress...",
                        "Quality control checks...",
                        "Library preparation complete"
                    ],
                    "ngs": [
                        "Initializing variant discovery...",
                        "Querying variant databases...",
                        "Calling variants for selected genes...",
                        "Processing allele frequencies...",
                        "Variant calling complete"
                    ],
                    "annotation": [
                        "Fetching clinical significance data...",
                        "Enriching with PharmGKB annotations...",
                        "Mapping to SNOMED CT ontology...",
                        "Clinical annotation complete"
                    ],
                    "enrichment": [
                        "Linking to drug databases...",
                        "Querying OpenFDA for drug labels...",
                        "Fetching ChEMBL drug interactions...",
                        "Finding disease associations...",
                        "Searching literature databases...",
                        "Drug-disease linking complete"
                    ],
                    "linking": [
                        "Connecting patient profile to variants...",
                        "Analyzing drug-gene interactions...",
                        "Checking for clinical conflicts...",
                        "Profile linking complete"
                    ],
                    "report": [
                        "Building RDF knowledge graph...",
                        "Merging all gene data...",
                        "Generating comprehensive JSON-LD...",
                        "Creating RDF triples...",
                        "Generating HTML reports...",
                        "Export complete"
                    ]
                }

                current_stage = [None]
                substep_index = [0]

                def process_event(event):
                    """Process a single event and update UI - MAIN THREAD ONLY"""
                    stage_progress_map = {
                        "lab_prep": (0.0, 0.2),
                        "ngs": (0.2, 0.4),
                        "annotation": (0.4, 0.6),
                        "enrichment": (0.6, 0.8),
                        "linking": (0.8, 0.9),
                        "report": (0.9, 1.0)
                    }

                    stage = event.stage

                    # Update stage if changed
                    if current_stage[0] != stage:
                        current_stage[0] = stage
                        substep_index[0] = 0

                    # Get progress range for this stage
                    if stage in stage_progress_map:
                        start_prog, end_prog = stage_progress_map[stage]

                        # Get substeps for this stage
                        substeps = stage_substeps.get(stage, [])
                        if substeps:
                            # Calculate progress within stage
                            substep_progress = substep_index[0] / len(substeps)
                            progress = start_prog + (end_prog - start_prog) * substep_progress

                            # Increment substep
                            substep_index[0] = min(substep_index[0] + 1, len(substeps) - 1)

                            # Show current substep
                            # Suppress legacy substep text; storyboard shows microsteps
                        else:
                            progress = start_prog
                    else:
                        progress = current_progress[0]

                    current_progress[0] = progress

                    # Main status message
                    # Suppress old emoji status line; storyboard shows messages

                # Snapshot selected genes from session in main thread
                selected_genes_snapshot = list(st.session_state.get('selected_genes', []) or [])

            # Prepare enhanced storyboard in Run Test (real pipeline)
                try:
                    # Reset storyboard placeholder so we don't stack instances
                    if not st.session_state.get('_sb_initialized'):
                        st.session_state['_pgx_storyboard_ph'] = st.empty()
                        sb = Storyboard() if 'Storyboard' in globals() and Storyboard else None
                        if sb and hasattr(sb, 'set_genes'):
                            sb.set_genes(st.session_state.get('selected_genes', []))
                    # Independent storyboard playback (not tightly synced)
                    # Use a comfortable fixed speed (ms) without exposing UI controls
                    storyboard_speed = 10000
                    # Build a reasonable plan matching pipeline stages
                    sb_plan = [
                        ("lab_prep", "init", "Starting lab preparation...", 0.06),
                        ("lab_prep", "qaqc", "QC checks passed", 0.18),
                        ("ngs", "seq", "Sequencing reads being generated...", 0.30),
                        ("ngs", "call", "Variant calling in progress...", 0.40),
                        ("annotation", "clinvar", "Annotating variants with ClinVar...", 0.52),
                        ("annotation", "literature", "Searching literature databases...", 0.64),
                        ("enrichment", "link", "Linking variants to drugs/diseases...", 0.76),
                        ("linking", "conflicts", "Checking for clinical conflicts...", 0.86),
                        ("report", "export", "Generating reports and visualizations...", 0.96),
                        ("report", "complete", "Storyboard complete", 1.00),
                    ]
                    if sb and hasattr(sb, 'set_demo_plan') and hasattr(sb, 'render') and not st.session_state.get('_sb_initialized'):
                        sb.set_demo_plan([
                            {"stage": s, "substage": sub, "message": msg, "progress": prog}
                            for s, sub, msg, prog in sb_plan
                        ], storyboard_speed)
                        sb.render("Initializing storyboard...")
                        st.session_state['_sb_initialized'] = True
                    # Estimate when storyboard finishes (ms per step × steps + small buffer)
                    storyboard_finish_time = time.time() + (storyboard_speed/1000.0) * max(1, len(sb_plan)) + 1.0
                except Exception:
                    sb = None

                # Worker function that runs pipeline in background thread
                def run_pipeline_worker():
                    """Run pipeline in background thread and put result in queue"""
                    try:
                        # Ensure we use the latest PGxPipeline definition (avoid stale module)
                        FreshPG = None
                        try:
                            import importlib, sys as _sys
                            if "src.main" in _sys.modules:
                                importlib.reload(_sys.modules["src.main"])  # type: ignore
                                from src.main import PGxPipeline as _Fresh
                                FreshPG = _Fresh
                            elif "main" in _sys.modules:
                                importlib.reload(_sys.modules["main"])  # type: ignore
                                from main import PGxPipeline as _Fresh
                                FreshPG = _Fresh
                            else:
                                try:
                                    from src.main import PGxPipeline as _Fresh
                                    FreshPG = _Fresh
                                except Exception:
                                    from main import PGxPipeline as _Fresh
                                    FreshPG = _Fresh
                        except Exception:
                            pass

                        PGClass = FreshPG or PGxPipeline
                        if not callable(PGClass):
                            raise RuntimeError("PGxPipeline class is not callable (import failed or stale module)")

                        # Create pipeline with event queue (thread-safe)
                        pipeline = PGClass(config_path=config_path, event_queue=event_queue)

                        # Run multi-gene analysis
                        result = pipeline.run_multi_gene(
                            gene_symbols=selected_genes_snapshot,
                            patient_profile=profile
                        )
                        result_queue.put({"success": True, "data": result})
                    except Exception as e:
                        import traceback
                        result_queue.put({
                            "success": False,
                            "error": str(e),
                            "traceback": traceback.format_exc()
                        })

                # Start worker thread
                worker = threading.Thread(target=run_pipeline_worker, daemon=True)
                worker.start()

                # Event consumption loop - RUNS IN MAIN THREAD
                # This is safe for Streamlit as all UI updates happen in main thread
                results = None
                worker_done = False
                last_update = time.time()
                update_interval = 0.1  # Update UI every 100ms max

                # Post-storyboard sections rendered flag
                extra_sections_shown = False
                
                while not worker_done:
                    # Process all available events (batch processing for performance)
                    events_processed = 0
                    while not event_queue.empty() and events_processed < 10:
                        try:
                            event = event_queue.get_nowait()
                            # Only update UI if enough time passed (throttling)
                            if time.time() - last_update > update_interval:
                                process_event(event)
                                last_update = time.time()
                            events_processed += 1
                        except queue.Empty:
                            break

                    # Check if worker is done
                    if not result_queue.empty():
                        result_data = result_queue.get()
                        if result_data["success"]:
                            results = result_data["data"]
                        else:
                            # Re-raise exception from worker
                            tb = result_data.get("traceback")
                            if tb:
                                # Also print full worker traceback to console for debugging
                                print("Worker traceback:\n" + tb)
                                raise RuntimeError(result_data["error"] + "\n" + tb)
                            raise RuntimeError(result_data["error"])
                        worker_done = True
                    elif not worker.is_alive():
                        # Worker died without putting result
                        worker_done = True

                    # If storyboard has completed but backend still running, show extra sections once
                    if not extra_sections_shown and time.time() > storyboard_finish_time and results is None:
                        # Update storyboard with a small post-processing plan for visual continuity
                        try:
                            if sb and hasattr(sb, 'set_demo_plan') and hasattr(sb, 'render'):
                                post_plan = [
                                    {"stage": "report", "substage": "finalize_graphs", "message": "Assembling knowledge graphs...", "progress": 0.98},
                                    {"stage": "report", "substage": "export_reports", "message": "Exporting reports...", "progress": 0.99},
                                    {"stage": "report", "substage": "quality_checks", "message": "Quality checks...", "progress": 0.995}
                                ]
                                # Reuse the same speed to keep feel consistent
                                sb.set_demo_plan(post_plan, storyboard_speed)
                                sb.render("Finalizing outputs...")
                        except Exception:
                            pass
                        extra_sections_shown = True

                    # Small sleep to prevent busy waiting
                    time.sleep(0.05)

                # Process any remaining events
                while not event_queue.empty():
                    try:
                        event = event_queue.get_nowait()
                        process_event(event)
                    except queue.Empty:
                        break

                # Sections under storyboard have been removed per request; storyboard continues to show progress

                # Ensure results is not None
                if results is None:
                    raise RuntimeError("Pipeline completed but no results were returned")
                
                # Complete progress handled by storyboard
                
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
                st.success("✅ Analysis Complete!")
                st.info("➡️ **Next:** Go to **📊 View Results** to see the full report and interactive knowledge graph.")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Variants Found", results.get('total_variants', 0))
                col2.metric("Genes Analyzed", len(results.get('genes', [])))
                col3.metric("Affected Drugs", results.get('affected_drugs', 0))
                col4.metric("Patient ID", results.get('patient_id', 'N/A'))

                # Show whether dashboard profile used
                used_dashboard = results.get('dashboard_source', False)
                if used_dashboard:
                    st.success("✅ Used dashboard patient profile")
                    # Show patient name from profile
                    cp = results.get('comprehensive_profile', {}) or {}
                    patient_name = cp.get('name', 'Unknown')
                    st.info(f"**Patient:** {patient_name}")
                else:
                    st.warning("⚠️ Used auto-generated profile")

                if 'comprehensive_outputs' in results and results['comprehensive_outputs']:
                    st.subheader("Generated Files")
                    for t, p in results['comprehensive_outputs'].items():
                        st.text(f"• {t}: {p}")
            else:
                st.error(f"❌ Test failed: {results.get('error', 'Unknown error')}")

elif page == "📊 View Results":
    st.title("📊 Clinical Report")
    st.info("**Step 4:** View the comprehensive analysis results, summary metrics, and interactive knowledge graph.")
    
    results = st.session_state.get('test_results')
    if not results:
        st.warning("⚠️ No results available. Please run a test first (Step 3)")
        st.stop()
    else:
        demo = (st.session_state.get('patient_profile') or {}).get('demographics', {})
        profile = st.session_state.get('patient_profile', {})
        
        # Display patient photo and information
        photo_col, info_col = st.columns([1, 3])
        with photo_col:
            if profile.get('photo'):
                st.image(profile['photo'], width=150, caption="Patient Photo")
            else:
                st.info("No photo available")
        
        with info_col:
            st.header("Patient Information")
            st.write(f"**Name:** {demo.get('first_name', '')} {demo.get('last_name', '')}")
            st.write(f"**MRN:** {demo.get('mrn', 'N/A')}")
            st.write(f"**Age:** {demo.get('age', 'N/A')}")

        st.header("📋 Analysis Summary")
        
        # Key metrics in columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Genes Analyzed", len(results.get('genes', [])))
            st.caption(", ".join(results.get('genes', [])))
        with col2:
            st.metric("Total Variants Found", results.get('total_variants', 0))
        with col3:
            st.metric("Affected Drugs", results.get('affected_drugs', 0))
        
        # Profile source
        dashboard_source = results.get('dashboard_source', False)
        profile_source = "✅ Dashboard Profile" if dashboard_source else "⚠️ Auto-generated Profile"
        st.info(f"**Data Source:** {profile_source}")
        
        # Show patient name if available
        cp = results.get('comprehensive_profile', {}) or {}
        patient_name = cp.get('name', '')
        if patient_name:
            st.caption(f"Patient: {patient_name}")
        
        # Additional summary info
        with st.expander("📊 Detailed Summary", expanded=False):
            st.json({
                "patient_id": results.get('patient_id', 'N/A'),
                "genes": results.get('genes', []),
                "total_variants": results.get('total_variants', 0),
                "affected_drugs": results.get('affected_drugs', 0),
                "timestamp": results.get('timestamp', 'N/A')
            })

        # Show generated files
        outputs = results.get('comprehensive_outputs', {}) or results.get('outputs', {})
        if outputs:
            st.header("Generated Files")
            with st.expander("📁 Output Files", expanded=False):
                for t, p in outputs.items():
                    st.text(f"{t}: {p}")
        
        # Interactive Visualization Section
        st.header("Interactive Knowledge Graph")
        if render_d3_visualization is None:
            st.error("Visualization component is not available.")
        else:
            # Try to find the comprehensive JSON-LD file (now contains all gene data merged)
            jsonld_path_str = None
            
            # First priority: Comprehensive JSON-LD (contains ALL genes merged)
            for key in ['JSON-LD', 'Comprehensive JSON-LD', 'Comprehensive Profile']:
                jsonld_path_str = outputs.get(key)
                if jsonld_path_str:
                    break
            
            # Second priority: Gene-specific knowledge graphs (fallback for individual genes)
            if not jsonld_path_str:
                for key in outputs.keys():
                    if 'knowledge graph' in key.lower():
                        jsonld_path_str = outputs.get(key)
                        break
            
            # Third priority: Search for any .jsonld files
            if not jsonld_path_str:
                for key, path in outputs.items():
                    if path and '.jsonld' in str(path):
                        jsonld_path_str = path
                        break
            
            # Get all available JSON-LD files
            all_jsonld_files = {}
            for key, path in outputs.items():
                if path and '.jsonld' in str(path) and Path(path).exists():
                    all_jsonld_files[key] = path
            
            # If multiple files, let user choose
            if len(all_jsonld_files) > 1:
                st.write("**Select JSON-LD file to visualize:**")
                file_options = list(all_jsonld_files.keys())
                
                # Set default based on our priority
                default_idx = 0
                for i, key in enumerate(file_options):
                    path = all_jsonld_files[key]
                    if 'patient' not in str(path).lower() and 'profile' not in str(path).lower():
                        default_idx = i
                        break
                
                selected_key = st.selectbox(
                    "Choose file:",
                    file_options,
                    index=default_idx,
                    key="jsonld_file_selector"
                )
                jsonld_path_str = all_jsonld_files[selected_key]
            elif len(all_jsonld_files) == 1:
                selected_key = list(all_jsonld_files.keys())[0]
                jsonld_path_str = all_jsonld_files[selected_key]
                st.caption(f"📄 Visualizing: {selected_key}")
            
            # Debug info
            with st.expander("🔍 File Selection Debug", expanded=False):
                st.write(f"All outputs: {list(outputs.keys())}")
                st.write(f"Available JSON-LD files: {list(all_jsonld_files.keys())}")
                st.write(f"Selected file: {jsonld_path_str}")
            
            if jsonld_path_str and Path(jsonld_path_str).exists():
                try:
                    with open(jsonld_path_str, 'r', encoding='utf-8') as f:
                        jsonld_data = json.load(f)

                        # Info about the visualization
                        st.info("💡 **Tip:** Click on nodes to see details, use mouse wheel to zoom, drag to pan. Use the controls to reset zoom or expand/collapse all nodes.")

                    with st.spinner("Generating interactive graph..."):
                        hierarchy_data = jsonld_to_hierarchy(jsonld_data)
                        if hierarchy_data:
                            # Render full-width visualization (no separate node details panel)
                            _ = render_d3_visualization(hierarchy_data)
                        else:
                            st.warning("Could not generate hierarchy from JSON-LD data.")

                except Exception as e:
                    st.error(f"Error loading visualization: {e}")
                    with st.expander("Debug Info"):
                        st.write(f"Path attempted: {jsonld_path_str}")
                        st.write(f"Available outputs: {list(outputs.keys())}")
                        import traceback
                        st.code(traceback.format_exc())
            else:
                st.warning("Comprehensive JSON-LD file not found. Cannot render visualization.")
                with st.expander("🔍 Debug - Available Files"):
                    st.write(f"Looking for JSON-LD in: {list(outputs.keys())}")
                    if jsonld_path_str:
                        st.write(f"Found path but file doesn't exist: {jsonld_path_str}")
                    else:
                        st.write("No JSON-LD key found in outputs")

elif page == "💾 Export Data":
    st.title("💾 Export Data")
    st.info("**Step 5:** Download all generated files including JSON-LD, RDF/TTL, and HTML reports.")
    
    results = st.session_state.get('test_results')
    if not results:
        st.warning("⚠️ No results to export. Please run a test first (Step 3)")
        st.stop()
    else:
        outputs = results.get('comprehensive_outputs', {}) or results.get('outputs', {})
        from pathlib import Path as _P
        
        if not outputs:
            st.warning("No output files found in results")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📥 Downloads")
                
                # Group files by type
                file_groups = {
                    "JSON-LD Files": [k for k in outputs.keys() if 'jsonld' in k.lower() or k.endswith('.jsonld')],
                    "RDF/TTL Files": [k for k in outputs.keys() if 'ttl' in k.lower() or k.endswith('.ttl')],
                    "HTML Reports": [k for k in outputs.keys() if 'html' in k.lower() or k.endswith('.html')],
                    "Other Files": []
                }
                
                # Add files that don't match any category to "Other"
                categorized = set()
                for group in file_groups.values():
                    categorized.update(group)
                file_groups["Other Files"] = [k for k in outputs.keys() if k not in categorized]
                
                # Display download buttons by group
                for group_name, file_keys in file_groups.items():
                    if file_keys:
                        st.markdown(f"**{group_name}**")
                        for key in file_keys:
                            path = outputs.get(key)
                            if path and _P(path).exists():
                                try:
                                    with open(path, 'rb') as f:
                                        file_content = f.read()
                                        st.download_button(
                                            f"📄 {key}",
                                            file_content,
                                            file_name=_P(path).name,
                                            key=f"download_{key}",
                                            use_container_width=False
                                        )
                                except Exception as e:
                                    st.error(f"Error reading {key}: {e}")
                            else:
                                st.caption(f"⚠️ {key} - File not found")
                        st.divider()
            
            with col2:
                st.subheader("📂 File Paths")
                for t, p in outputs.items():
                    exists = _P(p).exists() if p else False
                    status = "✅" if exists else "❌"
                    st.text(f"{status} {t}")
                    st.code(p or 'No path', language=None)

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

            st.divider()
            st.subheader("Auto Demo")
            demo_delay_ms = st.slider("Demo speed per step (ms)", min_value=200, max_value=3000, value=900, step=100, key="sb_demo_delay")
            if st.button("▶ Run storyboard simulation", key="run_storyboard_demo"):
                import queue as _q
                import time as _t

                # Instantiate a fresh storyboard and set example genes
                # Reset storyboard placeholder so we don't stack instances
                st.session_state['_pgx_storyboard_ph'] = st.empty()
                sb = Storyboard() if Storyboard else None
                if sb and hasattr(sb, 'set_genes'):
                    sb.set_genes(["CYP2D6", "CYP2C19", "TPMT", "DPYD"]) 

                # Full pass of stages (target progress per stage)
                demo_events = [
                    ("lab_prep", "init", "Starting lab preparation...", 0.05),
                    ("lab_prep", "qaqc", "DNA extracted and QC passed", 0.18),
                    ("ngs", "seq", "Sequencing reads being generated...", 0.30),
                    ("ngs", "call", "Variant calling in progress...", 0.38),
                    ("annotation", "clinvar", "Annotating variants with ClinVar...", 0.50),
                    ("annotation", "literature", "Searching literature databases...", 0.62),
                    ("enrichment", "link", "Linking variants to drugs/diseases...", 0.75),
                    ("linking", "conflicts", "Checking for clinical conflicts...", 0.85),
                    ("report", "export", "Generating reports and visualizations...", 0.95),
                    ("report", "complete", "Analysis complete!", 1.00),
                ]
                if sb and hasattr(sb, 'set_demo_plan'):
                    plan = [{"stage": s, "substage": sub, "message": msg, "progress": prog} for s, sub, msg, prog in demo_events]
                    sb.set_demo_plan(plan, demo_delay_ms)
                    sb.render("Starting demo...")
                else:
                    st.info("Storyboard runtime not available")

        except Exception as e:
            st.error(f"Storyboard error: {e}")
    else:
        st.info("Storyboard control helper not available")

else:
    st.error("Unknown page")
