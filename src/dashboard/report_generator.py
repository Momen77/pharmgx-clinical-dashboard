"""
Clinical report generator for HTML display
"""
import streamlit as st
from datetime import datetime
from dashboard.alert_classifier import AlertClassifier


class ReportGenerator:
    """Generates clinical pharmacogenomics reports"""
    
    def __init__(self):
        self.alert_classifier = AlertClassifier()
    
    def render_report(self, patient_profile: dict, test_results: dict):
        """Render comprehensive clinical report"""
        
        # Header with patient photo
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if patient_profile.get('photo'):
                st.image(patient_profile['photo'], width=150)
            else:
                st.info("No photo")
        
        with col2:
            demo = patient_profile.get('demographics', {})
            st.title(f"{demo.get('first_name', '')} {demo.get('last_name', '')}")
            st.write(f"**MRN:** {demo.get('mrn', 'N/A')}")
            st.write(f"**DOB:** {demo.get('date_of_birth', 'N/A')}")
            st.write(f"**Age:** {demo.get('age', 'N/A')} years")
        
        with col3:
            st.write(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d')}")
            st.write(f"**Report ID:** PGX-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        
        st.divider()
        
        # Summary section
        st.header("📋 Executive Summary")
        
        genes = test_results.get('genes', [])
        variants = test_results.get('total_variants', 0)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Genes Analyzed", len(genes))
        with col2:
            st.metric("Variants Found", variants)
        with col3:
            conflicts = test_results.get('comprehensive_outputs', {}).get('critical_conflicts', 0)
            st.metric("Critical Alerts", conflicts, delta_color="inverse")
        
        # Critical alerts
        if conflicts > 0:
            st.error(f"🚨 {conflicts} critical drug-gene interactions detected requiring immediate attention")
        
        st.divider()
        
        # Gene results
        st.header("🧬 Gene Results")
        
        for gene in genes:
            with st.expander(f"**{gene}** - Results", expanded=False):
                st.write(f"Gene: {gene}")
                st.write("Variant analysis results will be displayed here")
                st.write("Loading from comprehensive output files...")
        
        # Drug interactions
        st.header("💊 Drug-Gene Interactions")
        st.info("Drug interaction matrix will be displayed here")
        
        # Clinical recommendations
        st.header("⚕️ Clinical Recommendations")
        st.info("Clinical recommendations based on CPIC guidelines will be displayed here")
        
        return True

