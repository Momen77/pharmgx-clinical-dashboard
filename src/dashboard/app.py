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

# Add paths for module resolution
sys.path.insert(0, str(dashboard_dir))
sys.path.insert(0, str(src_dir))

# Import dashboard modules
from utils.styling import inject_css
from patient_creator import PatientCreator
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
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        bioportal_key = config.get('api', {}).get('bioportal_api_key')
    except:
        bioportal_key = None
    
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
        selector = GenePanelSelector()
        patient_profile = st.session_state.get('patient_profile')
        
        test_button = selector.render_test_button(
            st.session_state['selected_genes'],
            patient_profile
        )
        
        if test_button:
            st.session_state['test_running'] = True
            
            # Show progress
            with st.spinner("Running test..."):
                selector.render_test_progress(st.session_state['selected_genes'])
            
            # Actually run the pipeline
            if PGxKGPipeline is None:
                st.error("Pipeline not available. Please check imports.")
            else:
                try:
                    with st.spinner("Executing PGx pipeline..."):
                        pipeline = PGxKGPipeline(config_path="config.yaml")
                        results = pipeline.run_multi_gene(st.session_state['selected_genes'])
                        
                        st.session_state['test_results'] = results
                        st.session_state['test_running'] = False
                        st.session_state['test_complete'] = True
                        
                        # Show success screen
                        st.success("✅ Pharmacogenetic Test Complete!")
                        
                        # Summary metrics
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
                        
                        st.info("📊 View the detailed report in the 'View Report' page")
                        
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

