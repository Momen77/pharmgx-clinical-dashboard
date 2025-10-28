"""
Main Streamlit Dashboard Application
Clinical Pharmacogenomics Testing Dashboard
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Add current directory and parent to path for imports
dashboard_dir = Path(__file__).parent
src_dir = dashboard_dir.parent
project_root = src_dir.parent

# Add paths for module resolution (ensure dashboard directory is first)
if str(dashboard_dir) not in sys.path:
    sys.path.insert(0, str(dashboard_dir))
if str(src_dir) not in sys.path:
    sys.path.insert(1, str(src_dir))
if str(project_root) not in sys.path:
    sys.path.insert(2, str(project_root))

# Import dashboard modules - specifically from dashboard.utils
try:
    from dashboard.utils.styling import inject_css
except ImportError as e:
    try:
        # Try relative import within dashboard package
        from .utils.styling import inject_css
    except ImportError:
        try:
            # Fallback: direct import from file using importlib
            import importlib.util
            utils_path = dashboard_dir / "utils" / "styling.py"
            if utils_path.exists():
                spec = importlib.util.spec_from_file_location("styling", utils_path)
                styling_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(styling_module)
                inject_css = styling_module.inject_css
            else:
                st.error(f"Could not find styling.py at {utils_path}")
                def inject_css():
                    st.markdown("<!-- Styling module not found -->", unsafe_allow_html=True)
        except Exception as import_error:
            st.error(f"Could not load styling module: {import_error}")
            def inject_css():
                st.markdown("<!-- Styling module not loaded -->", unsafe_allow_html=True)

from patient_creator import PatientCreator
from ui_profile import render_profile_controls, render_manual_enrichment_forms
from ui_animation import Storyboard, consume_events
from gene_panel_selector import GenePanelSelector
from alert_classifier import AlertClassifier

# Import main pipeline
try:
    from src.main import PGxKGPipeline
except ImportError:
    try:
        from main import PGxKGPipeline
    except ImportError:
        st.error("Could not import PGxKGPipeline. Please ensure main.py is accessible.")
        PGxKGPipeline = None

# Page configuration
st.set_page_config(
    page_title="UGent PGx Dashboard",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Ghent University CSS
inject_css()

# Initialize session state
if 'patient_created' not in st.session_state:
    st.session_state['patient_created'] = False
if 'selected_genes' not in st.session_state:
    st.session_state['selected_genes'] = []
if 'test_results' not in st.session_state:
    st.session_state['test_results'] = None
if 'test_running' not in st.session_state:
    st.session_state['test_running'] = False

# Sidebar navigation
with st.sidebar:
    st.image("https://via.placeholder.com/200x60/1E64C8/FFFFFF?text=UGent+PGx", use_container_width=True)
    st.title("Navigation")
    
    page = st.radio(
        "Select Page",
        ["🏠 Home", "👤 Create Patient", "🧬 Select Genes", "🔬 Run Test", "📊 View Report", "💾 Export Data"],
        index=0
    )

# Main content area
if page == "🏠 Home":
    st.title("🧬 UGent Pharmacogenomics Testing Dashboard")
    st.markdown("Welcome to the Clinical Pharmacogenomics Testing Platform")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Patients Tested", "1,234")
    with col2:
        st.metric("Genes Analyzed", "25+")
    with col3:
        st.metric("Drug Interactions", "500+")
    
    st.info("👆 Use the sidebar to navigate through the testing workflow")

elif page == "👤 Create Patient":
    # Load config for API keys
    try:
        import yaml
        # Try to find config.yaml in multiple locations
        config_paths = [
            project_root / "config.yaml",  # Root config.yaml
            src_dir.parent / "config.yaml",  # Dashboard parent
            dashboard_dir.parent / "config.yaml",  # Alternative location
            Path("config.yaml")  # Current directory
        ]
        
        config = None
        for config_path in config_paths:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                break
        
        if config:
            bioportal_key = config.get('api', {}).get('bioportal_api_key')
        else:
            bioportal_key = None
            st.warning("⚠️ Could not find config.yaml. API features may be limited.")
    except Exception as e:
        bioportal_key = None
        st.warning(f"⚠️ Could not load API keys: {e}")
    
    creator = PatientCreator(bioportal_api_key=bioportal_key)
    creator.render_patient_form()

elif page == "🧬 Select Genes":
    selector = GenePanelSelector()
    selected_genes = selector.render_gene_selector()
    
    if selected_genes:
        st.session_state['selected_genes'] = selected_genes

elif page == "🔬 Run Test":
    st.title("🔬 Run Pharmacogenetic Test")
    
    # Check prerequisites
    if not st.session_state.get('patient_created'):
        st.warning("⚠️ Please create a patient profile first")
        st.info("Go to 'Create Patient' page in the sidebar")
    
    if not st.session_state.get('selected_genes'):
        st.warning("⚠️ Please select genes to test")
        st.info("Go to 'Select Genes' page in the sidebar")
    
    if st.session_state.get('patient_created') and st.session_state.get('selected_genes'):
        # Demo mode toggle
        demo_mode = st.checkbox("Demo mode (simulated pipeline)", value=False, help="Use simulated pipeline for testing UI")
        
        # Profile controls
        mode, enrich = render_profile_controls()
        manual_conditions = []
        manual_meds = []
        manual_labs = {}
        if enrich == "Manual (enter now)":
            manual_conditions, manual_meds, manual_labs = render_manual_enrichment_forms()
        selector = GenePanelSelector()
        patient_profile = st.session_state.get('patient_profile')
        
        test_button = selector.render_test_button(
            st.session_state['selected_genes'],
            patient_profile
        )
        
        if test_button:
            st.session_state['test_running'] = True
            
            # Background worker + storyboard
            if PGxKGPipeline is None:
                st.error("Pipeline not available. Please check imports.")
            else:
                try:
                    import queue as _q
                    from utils.background_worker import PipelineWorker
                    from utils.event_bus import PipelineEvent

                    # Resolve config path
                    config_paths = [
                        project_root / "config.yaml",
                        src_dir.parent / "config.yaml",
                        dashboard_dir.parent / "config.yaml",
                        Path("config.yaml")
                    ]
                    config_path = "config.yaml"
                    for cp in config_paths:
                        if cp.exists():
                            config_path = str(cp)
                            break

                    event_q = _q.Queue()
                    result_q = _q.Queue()
                    cancel_flag = __import__("threading").Event()

                    # Prepare profile base
                    profile = st.session_state.get('patient_profile', {})
                    if enrich == "Auto (by age/lifestyle)":
                        profile.setdefault('auto_enrichment', True)
                    elif enrich == "Manual (enter now)":
                        profile.setdefault('manual_enrichment', {})
                        if manual_conditions:
                            profile['manual_enrichment']['conditions'] = manual_conditions
                        if manual_meds:
                            profile['manual_enrichment']['medications'] = manual_meds
                        if manual_labs:
                            profile['manual_enrichment']['labs'] = manual_labs

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

                    storyboard = Storyboard()
                    
                    # Cancel button
                    cancel_col, status_col = st.columns([1, 3])
                    with cancel_col:
                        if st.button("Cancel Run", type="secondary"):
                            cancel_flag.set()
                            st.warning("Cancelling pipeline...")
                    
                    with status_col:
                        st.info("🔄 Pipeline running... Check animation above for progress")
                    
                    consume_events(event_q, storyboard, worker_alive_fn=lambda: worker.is_alive())

                    # Get result
                    if not result_q.empty():
                        results = result_q.get()
                    else:
                        results = {"success": False, "error": "No result from worker"}

                    if results.get('success'):
                        st.session_state['test_results'] = results
                        st.session_state['test_complete'] = True
                        st.success("✅ Pharmacogenetic Test Complete!")
                        
                        # Enhanced results display
                        st.header("📊 Results Summary")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Variants Found", results.get('total_variants', 0))
                        with col2:
                            st.metric("Genes Analyzed", len(results.get('genes', [])))
                        with col3:
                            critical_count = results.get('comprehensive_outputs', {}).get('critical_conflicts', 0)
                            st.metric("Critical Alerts", critical_count, delta_color="inverse")
                        with col4:
                            st.metric("Affected Drugs", results.get('affected_drugs', 0))
                        
                        # Show generated files
                        if 'comprehensive_outputs' in results and results['comprehensive_outputs']:
                            st.subheader("📁 Generated Files")
                            for file_type, file_path in results['comprehensive_outputs'].items():
                                st.text(f"• {file_type}: {file_path}")
                        
                        st.info("📊 View the detailed report in the 'View Report' page")
                    else:
                        st.error(f"❌ Test failed: {results.get('error')}")
                        
                except Exception as e:
                    st.error(f"❌ Test failed: {str(e)}")
                    st.session_state['test_running'] = False
                
                finally:
                    st.session_state['test_running'] = False

elif page == "📊 View Report":
    st.title("📊 Clinical Report")
    
    if not st.session_state.get('test_results'):
        st.warning("⚠️ No test results available. Please run a test first.")
    else:
        results = st.session_state['test_results']
        patient_profile = st.session_state.get('patient_profile', {})
        
        # Display report (simplified for now)
        st.header("Patient Information")
        if patient_profile:
            demo = patient_profile.get('demographics', {})
            st.write(f"**Name:** {demo.get('first_name', '')} {demo.get('last_name', '')}")
            st.write(f"**MRN:** {demo.get('mrn', 'N/A')}")
            st.write(f"**Age:** {demo.get('age', 'N/A')} years")
        
        st.header("Test Results Summary")
        st.write(f"**Genes Analyzed:** {', '.join(results.get('genes', []))}")
        st.write(f"**Total Variants:** {results.get('total_variants', 0)}")
        
        # Show outputs
        if 'comprehensive_outputs' in results:
            outputs = results['comprehensive_outputs']
            st.header("Generated Files")
            for output_type, path in outputs.items():
                st.text(f"{output_type}: {path}")

elif page == "💾 Export Data":
    st.title("💾 Export Data")
    
    if not st.session_state.get('test_results'):
        st.warning("⚠️ No test results available to export")
    else:
        results = st.session_state['test_results']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Export Options")
            if st.button("📄 Download PDF Report"):
                st.info("PDF export will be implemented with ReportLab")
            
            if st.button("📊 Download JSON-LD"):
                if 'comprehensive_outputs' in results:
                    jsonld_path = results['comprehensive_outputs'].get('Comprehensive JSON-LD')
                    if jsonld_path:
                        with open(jsonld_path, 'rb') as f:
                            st.download_button(
                                "Download JSON-LD",
                                f.read(),
                                file_name=f"patient_pgx_{datetime.now().strftime('%Y%m%d')}.jsonld",
                                mime="application/json"
                            )
        
        with col2:
            st.subheader("Raw Data Files")
            if 'comprehensive_outputs' in results:
                for file_type, file_path in results['comprehensive_outputs'].items():
                    st.text(f"• {file_type}")
                    st.code(file_path, language=None)

if __name__ == "__main__":
    pass

