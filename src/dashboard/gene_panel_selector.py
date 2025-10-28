"""
Gene panel selection interface with organized categories
"""
import streamlit as st

# Pre-defined gene panels organized by category
GENE_PANELS = {
    "Core Metabolizers": {
        "icon": "🔬",
        "genes": ["CYP2D6", "CYP2C19", "CYP2C9", "CYP3A4", "CYP3A5"],
        "description": "Most commonly tested pharmacogenes"
    },
    "Chemotherapy": {
        "icon": "💊",
        "genes": ["DPYD", "TPMT", "NUDT15", "UGT1A1"],
        "description": "Critical for chemotherapy safety"
    },
    "Transporters": {
        "icon": "🚚",
        "genes": ["SLCO1B1", "ABCB1", "ABCG2"],
        "description": "Drug transporter genes"
    },
    "Drug Targets": {
        "icon": "🎯",
        "genes": ["VKORC1", "HLA-B", "HLA-A", "G6PD"],
        "description": "Drug target and HLA genes"
    },
    "Oncology": {
        "icon": "🧬",
        "genes": ["KRAS", "TP53", "HER2", "MYC", "EGFR", "BRAF"],
        "description": "Oncology biomarkers"
    }
}

# Common FDA/CPIC biomarker panel
COMMON_PANEL = ["CYP2D6", "CYP2C19", "CYP2C9", "CYP3A4", "VKORC1", "SLCO1B1", "TPMT", "DPYD"]


class GenePanelSelector:
    """Gene panel selection interface"""
    
    def render_gene_selector(self):
        """Render gene selection interface with checkboxes"""
        st.header("🧬 Select Pharmacogenetic Panel")
        
        # Quick action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📋 Select Common Panel", width='stretch'):
                st.session_state['selected_genes'] = COMMON_PANEL.copy()
                st.rerun()
        
        with col2:
            if st.button("✨ Select All Clinically Actionable", width='stretch'):
                all_genes = []
                for panel in GENE_PANELS.values():
                    all_genes.extend(panel["genes"])
                st.session_state['selected_genes'] = list(set(all_genes))
                st.rerun()
        
        with col3:
            if st.button("🔄 Clear Selection", width='stretch'):
                st.session_state['selected_genes'] = []
                st.rerun()
        
        # Initialize selected genes in session state
        if 'selected_genes' not in st.session_state:
            st.session_state['selected_genes'] = []
        
        selected_genes = st.session_state['selected_genes']
        
        # Gene panels with checkboxes
        st.subheader("UGent PGx Gene Panel™")
        
        for category, panel_info in GENE_PANELS.items():
            with st.expander(f"{panel_info['icon']} {category} - {panel_info['description']}", expanded=True):
                cols = st.columns(3)
                genes = panel_info["genes"]
                
                for i, gene in enumerate(genes):
                    col_idx = i % 3
                    with cols[col_idx]:
                        is_selected = gene in selected_genes
                        checkbox = st.checkbox(
                            gene,
                            value=is_selected,
                            key=f"gene_{gene}"
                        )
                        
                        if checkbox and gene not in selected_genes:
                            selected_genes.append(gene)
                        elif not checkbox and gene in selected_genes:
                            selected_genes.remove(gene)
        
        # Custom gene input
        st.subheader("Custom Genes")
        custom_genes_text = st.text_input(
            "Enter additional genes (comma-separated)",
            value="",
            help="Example: CYP1A2, CYP2B6, NAT2"
        )
        
        if custom_genes_text:
            custom_genes = [g.strip().upper() for g in custom_genes_text.split(",") if g.strip()]
            for gene in custom_genes:
                if gene not in selected_genes:
                    selected_genes.append(gene)
        
        # Update session state
        st.session_state['selected_genes'] = selected_genes
        
        # Display selected genes summary
        if selected_genes:
            st.success(f"✅ {len(selected_genes)} genes selected")
            
            # Show selected genes in columns
            num_cols = min(5, len(selected_genes))
            cols = st.columns(num_cols)
            for i, gene in enumerate(selected_genes):
                with cols[i % num_cols]:
                    # Use badge-style display instead of st.tag() for compatibility
                    st.markdown(f'<div style="background-color: #1E64C8; color: white; padding: 5px 10px; border-radius: 15px; text-align: center; font-weight: bold;">{gene}</div>', unsafe_allow_html=True)
        else:
            st.info("👆 Select genes above to proceed with testing")
        
        return selected_genes
    
    def render_test_button(self, selected_genes: list, patient_profile: dict = None):
        """Render test execution button with workflow"""
        if not selected_genes:
            st.warning("⚠️ Please select at least one gene to test")
            return False
        
        st.divider()
        
        # Pre-test summary card
        if patient_profile:
            patient_name = f"{patient_profile['demographics']['first_name']} {patient_profile['demographics']['last_name']}"
            st.info(f"**Patient:** {patient_name} | **Genes:** {len(selected_genes)} | **Estimated time:** ~20 seconds")
        
        # Large test button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            test_button = st.button(
                "🧬 Run Pharmacogenetic Test",
                type="primary",
                width='stretch',
                key="run_test_button"
            )
        
        return test_button
    
    def render_test_progress(self, selected_genes: list):
        """Render test progress animation"""
        import time
        
        progress_bar = st.progress(0)
        status_container = st.empty()
        metrics_container = st.empty()
        
        # Generate random but realistic metrics
        import random
        dna_concentration = round(random.uniform(80, 90), 1)
        purity = round(random.uniform(1.75, 1.90), 2)
        variant_count = random.randint(5, 15)
        
        stages = [
            {
                "message": "🩸 Collecting sample...",
                "detail": "Using 5ml EDTA tube",
                "progress": 0.2,
                "duration": 3
            },
            {
                "message": "🧪 Extracting DNA...",
                "detail": f"DNA concentration: {dna_concentration} ng/μL | Purity: {purity} ✅",
                "progress": 0.4,
                "duration": 4
            },
            {
                "message": f"🔬 Sequencing {len(selected_genes)} genes...",
                "detail": f"Processing {len(selected_genes)} pharmacogenes",
                "progress": 0.7,
                "duration": 5
            },
            {
                "message": "💻 Analyzing variants...",
                "detail": f"Found {variant_count} variants | Determining diplotypes...",
                "progress": 0.9,
                "duration": 4
            },
            {
                "message": "📋 Generating report...",
                "detail": "Checking drug-gene interactions...",
                "progress": 1.0,
                "duration": 4
            }
        ]
        
        for stage in stages:
            status_container.markdown(f"### {stage['message']}")
            metrics_container.info(f"_{stage['detail']}_")
            progress_bar.progress(stage['progress'])
            time.sleep(stage['duration'])
            metrics_container.success(f"✅ {stage['detail']}")
        
        return True

