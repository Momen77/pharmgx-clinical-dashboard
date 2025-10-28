"""
Enhanced Workflow Animation for Human Pharmacogenetics
Detailed, illustrative, and fun visualization of the PGx workflow
"""
from __future__ import annotations

import streamlit as st
import time
from typing import Optional, Dict, Any, List

try:
    from .workflow_details import DETAIL_SCRIPTS, VISUAL_FLAGS, NETWORK_TEMPLATES
except ImportError:
    # Fallback if details not available
    DETAIL_SCRIPTS = {}
    VISUAL_FLAGS = {}
    NETWORK_TEMPLATES = {}

# Enhanced CSS with network visualization and detailed animations
_CSS_KEY = "_pgx_workflow_enhanced_css"

def _inject_enhanced_css():
    if st.session_state.get(_CSS_KEY):
        return
    st.markdown(
        """
        <style>
        /* Enhanced Workflow Styles */
        .wf-wrap { 
            border: 2px solid #e2e8f0; 
            border-radius: 12px; 
            padding: 20px; 
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); 
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }
        
        .wf-header {
            text-align: center;
            margin-bottom: 20px;
            font-size: 1.2rem;
            font-weight: 700;
            color: #1e40af;
        }
        
        .wf-stages {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        .wf-stage {
            flex: 1;
            min-width: 180px;
            padding: 12px;
            border-radius: 10px;
            border: 2px solid #e5e7eb;
            background: #ffffff;
            transition: all 300ms ease;
            position: relative;
        }
        
        .wf-stage.active {
            background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
            border-color: #3b82f6;
            transform: scale(1.02);
            box-shadow: 0 8px 25px rgba(59, 130, 246, 0.15);
        }
        
        .wf-stage.done {
            background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
            border-color: #22c55e;
        }
        
        .wf-stage-icon {
            font-size: 2rem;
            text-align: center;
            margin-bottom: 8px;
        }
        
        .wf-stage-title {
            font-weight: 600;
            font-size: 0.9rem;
            color: #1f2937;
            text-align: center;
            margin-bottom: 6px;
        }
        
        .wf-stage-detail {
            font-size: 0.75rem;
            color: #6b7280;
            text-align: center;
            line-height: 1.3;
        }
        
        .wf-microsteps {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid rgba(0,0,0,0.1);
        }
        
        .wf-microstep {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 4px 0;
            font-size: 0.75rem;
            color: #4b5563;
        }
        
        .wf-microstep.active {
            color: #1d4ed8;
            font-weight: 600;
        }
        
        .wf-microstep.done {
            color: #16a34a;
        }
        
        .wf-microstep-icon {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #d1d5db;
        }
        
        .wf-microstep.active .wf-microstep-icon {
            background: #3b82f6;
            animation: pulse 1.5s infinite;
        }
        
        .wf-microstep.done .wf-microstep-icon {
            background: #22c55e;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Network Graph Styles */
        .wf-network {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
            margin: 16px 0;
        }
        
        .wf-network-title {
            font-weight: 600;
            font-size: 0.9rem;
            color: #374151;
            margin-bottom: 12px;
            text-align: center;
        }
        
        .wf-network-graph {
            display: flex;
            flex-direction: column;
            gap: 12px;
            align-items: center;
        }
        
        .wf-network-row {
            display: flex;
            gap: 12px;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        .wf-network-node {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
            border: 2px solid transparent;
            background: #ffffff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .wf-network-node.medication {
            background: #fef3c7;
            border-color: #f59e0b;
            color: #92400e;
        }
        
        .wf-network-node.gene {
            background: #dbeafe;
            border-color: #3b82f6;
            color: #1d4ed8;
        }
        
        .wf-network-edge {
            width: 2px;
            height: 20px;
            background: #9ca3af;
            position: relative;
        }
        
        .wf-network-edge.warning {
            background: #f59e0b;
            animation: warning-pulse 2s infinite;
        }
        
        .wf-network-edge.critical {
            background: #dc2626;
            animation: critical-pulse 1s infinite;
        }
        
        @keyframes warning-pulse {
            0%, 100% { opacity: 0.7; }
            50% { opacity: 1; }
        }
        
        @keyframes critical-pulse {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; }
        }
        
        /* Counters and Meters */
        .wf-counter {
            display: inline-block;
            background: #3b82f6;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            min-width: 24px;
            text-align: center;
        }
        
        .wf-meter {
            width: 60px;
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin: 4px 0;
        }
        
        .wf-meter-fill {
            height: 100%;
            background: #22c55e;
            width: 0%;
            transition: width 500ms ease;
        }
        
        /* Gene Chips */
        .wf-gene-chips {
            display: flex;
            gap: 6px;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 8px;
        }
        
        .wf-gene-chip {
            padding: 4px 8px;
            background: #f3f4f6;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 500;
            color: #374151;
            transition: all 200ms ease;
        }
        
        .wf-gene-chip.active {
            background: #3b82f6;
            color: white;
            border-color: #2563eb;
            animation: chip-glow 1s infinite;
        }
        
        @keyframes chip-glow {
            0%, 100% { box-shadow: 0 0 8px rgba(59, 130, 246, 0.5); }
            50% { box-shadow: 0 0 16px rgba(59, 130, 246, 0.8); }
        }
        
        /* Progress Bar */
        .wf-progress {
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin: 16px 0 8px 0;
        }
        
        .wf-progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #06b6d4);
            width: 0%;
            transition: width 400ms ease;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state[_CSS_KEY] = True


class EnhancedStoryboardV2:
    """Enhanced workflow visualization with detailed PGx steps and network graph"""

    def __init__(self, genes: List[str] = None):
        _inject_enhanced_css()
        self.progress = 0.0
        self.stage = "lab"
        self.microstep = 0
        self.genes = genes or []
        self.state = {
            "variants": 0,
            "drugs": 0,
            "literature": 0,
            "current_gene": None,
            "coverage": 0,
            "depth": 0
        }
        self._container = st.container()
        self.render("Initializing pharmacogenetic analysis...")

    def render(self, caption: str = ""):
        """Render the enhanced workflow visualization"""
        with self._container:
            st.markdown("<div class='wf-wrap'>", unsafe_allow_html=True)
            st.markdown("<div class='wf-header'>🧬 Pharmacogenetic Analysis Workflow</div>", unsafe_allow_html=True)
            
            # Main stages
            st.markdown("<div class='wf-stages'>", unsafe_allow_html=True)
            
            stages = [
                ("lab", "🧪", "Lab Prep", "DNA extraction & library prep"),
                ("ngs", "🧬", "Sequencing", f"Variants: {self.state['variants']}"),
                ("anno", "🔬", "Annotation", f"Literature: {self.state['literature']}"),
                ("drug", "💊", "Interactions", f"Drugs: {self.state['drugs']}"),
                ("report", "📊", "Report", "Comprehensive results"),
            ]
            
            for stage_id, icon, title, subtitle in stages:
                css_class = "wf-stage"
                if stage_id == self.stage:
                    css_class += " active"
                elif self._is_stage_done(stage_id):
                    css_class += " done"
                
                stage_html = f"""
                <div class='{css_class}'>
                    <div class='wf-stage-icon'>{icon}</div>
                    <div class='wf-stage-title'>{title}</div>
                    <div class='wf-stage-detail'>{subtitle}</div>
                    {self._render_microsteps(stage_id)}
                    {self._render_stage_specific_content(stage_id)}
                </div>
                """
                st.markdown(stage_html, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)  # Close stages
            
            # Gene chips
            if self.genes:
                chips_html = "<div class='wf-gene-chips'>"
                for gene in self.genes:
                    chip_class = "wf-gene-chip"
                    if gene == self.state.get('current_gene'):
                        chip_class += " active"
                    chips_html += f"<span class='{chip_class}'>{gene}</span>"
                chips_html += "</div>"
                st.markdown(chips_html, unsafe_allow_html=True)
            
            # Network visualization for drug interactions stage
            if self.stage == "drug" and self.state['drugs'] > 0:
                self._render_network_graph()
            
            # Progress bar
            progress_html = f"""
            <div class='wf-progress'>
                <div class='wf-progress-fill' style='width: {self.progress * 100}%'></div>
            </div>
            """
            st.markdown(progress_html, unsafe_allow_html=True)
            
            if caption:
                st.caption(f"💬 {caption}")
            
            st.markdown("</div>", unsafe_allow_html=True)  # Close wrap

    def _is_stage_done(self, stage_id: str) -> bool:
        """Check if a stage is completed"""
        stage_order = ["lab", "ngs", "anno", "drug", "report"]
        current_idx = stage_order.index(self.stage) if self.stage in stage_order else 0
        check_idx = stage_order.index(stage_id) if stage_id in stage_order else 0
        return check_idx < current_idx

    def _render_microsteps(self, stage_id: str) -> str:
        """Render detailed microsteps for current stage"""
        if stage_id != self.stage or stage_id not in DETAIL_SCRIPTS:
            return ""
        
        steps = DETAIL_SCRIPTS[stage_id]
        if not steps:
            return ""
        
        html = "<div class='wf-microsteps'>"
        for i, step in enumerate(steps):
            step_class = "wf-microstep"
            if i < self.microstep:
                step_class += " done"
            elif i == self.microstep:
                step_class += " active"
            
            html += f"""
            <div class='{step_class}'>
                <span class='wf-microstep-icon'></span>
                <span title='{step["hint"]}'>{step["label"]}</span>
            </div>
            """
        html += "</div>"
        return html

    def _render_stage_specific_content(self, stage_id: str) -> str:
        """Render stage-specific visual elements"""
        if stage_id != self.stage:
            return ""
        
        if stage_id == "ngs":
            # Coverage and depth meters
            coverage = self.state.get('coverage', 0)
            depth = self.state.get('depth', 0)
            return f"""
            <div style='margin-top: 8px;'>
                <div style='font-size: 0.7rem; color: #6b7280;'>Coverage: {coverage}%</div>
                <div class='wf-meter'>
                    <div class='wf-meter-fill' style='width: {coverage}%'></div>
                </div>
                <div style='font-size: 0.7rem; color: #6b7280;'>Depth: {depth}x</div>
                <div class='wf-meter'>
                    <div class='wf-meter-fill' style='width: {min(depth/30*100, 100)}%'></div>
                </div>
            </div>
            """
        
        elif stage_id == "anno":
            # Database connection indicators
            dbs = ["dbSNP", "ClinVar", "PharmGKB"]
            db_html = "<div style='margin-top: 8px; font-size: 0.7rem; color: #6b7280;'>Connected: "
            db_html += ", ".join([f"<span style='color: #16a34a;'>{db}</span>" for db in dbs])
            db_html += "</div>"
            return db_html
        
        return ""

    def _render_network_graph(self):
        """Render drug-gene interaction network"""
        st.markdown("<div class='wf-network'>", unsafe_allow_html=True)
        st.markdown("<div class='wf-network-title'>🔗 Drug-Gene Interaction Network</div>", unsafe_allow_html=True)
        
        # Get medications and genes from templates
        meds = NETWORK_TEMPLATES.get('medications', [])[:3]  # Limit to 3 for clarity
        genes_data = NETWORK_TEMPLATES.get('genes', [])
        patient_genes = [g for g in genes_data if g['name'] in self.genes][:3]
        
        if meds and patient_genes:
            # Medications row
            meds_html = "<div class='wf-network-row'>"
            for med in meds:
                meds_html += f"<div class='wf-network-node medication' style='border-color: {med['color']};'>💊 {med['name']}</div>"
            meds_html += "</div>"
            
            # Connection edges
            edges_html = "<div class='wf-network-row'>"
            for i in range(min(len(meds), len(patient_genes))):
                edge_class = "wf-network-edge"
                if i % 2 == 0:  # Simulate some interactions
                    edge_class += " warning" if i == 0 else " critical"
                edges_html += f"<div class='{edge_class}'></div>"
            edges_html += "</div>"
            
            # Genes row
            genes_html = "<div class='wf-network-row'>"
            for gene in patient_genes:
                variants_str = ", ".join(gene.get('variants', [])[:2])
                genes_html += f"<div class='wf-network-node gene' style='border-color: {gene['color']};'>🧬 {gene['name']}<br><small>{variants_str}</small></div>"
            genes_html += "</div>"
            
            network_html = f"{meds_html}{edges_html}{genes_html}"
            st.markdown(network_html, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

    def advance(self, stage: str = None, message: str = "", progress: Optional[float] = None, 
                microstep: int = None, deltas: Optional[Dict[str, Any]] = None):
        """Advance the workflow with detailed micro-step control"""
        if stage and stage != self.stage:
            self.stage = stage
            self.microstep = 0  # Reset microsteps for new stage
        
        if microstep is not None:
            self.microstep = microstep
        
        if progress is not None:
            self.progress = max(0.0, min(1.0, progress))
        
        if deltas:
            for key, value in deltas.items():
                if key in self.state:
                    if isinstance(value, (int, float)):
                        self.state[key] = max(0, self.state[key] + value)
                    else:
                        self.state[key] = value
        
        self.render(message)

    def set_genes(self, genes: List[str]):
        """Set the genes being analyzed"""
        self.genes = genes or []


# Enhanced event consumer with detailed step progression
def consume_events_enhanced(event_q, storyboard: EnhancedStoryboardV2, worker_alive_fn):
    """Enhanced event consumer with micro-step progression"""
    import queue
    
    step_counters = {stage: 0 for stage in DETAIL_SCRIPTS.keys()}
    
    while worker_alive_fn() or not event_q.empty():
        try:
            event = event_q.get(timeout=0.1)
            if not event:
                continue
            
            stage = getattr(event, 'stage', None)
            message = getattr(event, 'message', '')
            progress = getattr(event, 'progress', None)
            
            # Map old stage names to new ones
            stage_map = {
                "lab_prep": "lab",
                "ngs": "ngs",
                "annotation": "anno",
                "enrichment": "drug",
                "linking": "drug",
                "report": "report",
                "export": "report"
            }
            
            mapped_stage = stage_map.get(stage, stage)
            
            # Auto-advance microsteps
            if mapped_stage in step_counters:
                max_steps = len(DETAIL_SCRIPTS.get(mapped_stage, []))
                if step_counters[mapped_stage] < max_steps:
                    step_counters[mapped_stage] += 1
            
            # Update counters based on message content
            deltas = {}
            msg_lower = message.lower()
            
            if mapped_stage == 'ngs':
                if 'variant' in msg_lower or 'calling' in msg_lower:
                    deltas['variants'] = 1
                if 'coverage' in msg_lower:
                    deltas['coverage'] = 5
                if 'depth' in msg_lower:
                    deltas['depth'] = 2
                # Set current gene being processed
                for gene in storyboard.genes:
                    if gene.lower() in msg_lower:
                        deltas['current_gene'] = gene
                        break
            
            elif mapped_stage == 'anno':
                if any(term in msg_lower for term in ['literature', 'pmid', 'europe', 'citation']):
                    deltas['literature'] = 1
            
            elif mapped_stage == 'drug':
                if any(term in msg_lower for term in ['drug', 'interaction', 'medication']):
                    deltas['drugs'] = 1
            
            storyboard.advance(
                stage=mapped_stage,
                message=message,
                progress=progress,
                microstep=step_counters.get(mapped_stage, 0),
                deltas=deltas
            )
            
        except queue.Empty:
            pass
        except Exception:
            pass


# Backward compatibility
class Storyboard:
    def __init__(self):
        self._enhanced = EnhancedStoryboardV2()
    
    def set_genes(self, genes):
        self._enhanced.set_genes(genes)
    
    def advance(self, event):
        if not event:
            return
        stage = getattr(event, 'stage', None)
        message = getattr(event, 'message', '')
        progress = getattr(event, 'progress', None)
        self._enhanced.advance(stage=stage, message=message, progress=progress)


def consume_events(event_q, storyboard: Storyboard, worker_alive_fn):
    """Backward compatible event consumer"""
    if hasattr(storyboard, '_enhanced'):
        return consume_events_enhanced(event_q, storyboard._enhanced, worker_alive_fn)
    # Fallback
    import queue
    while worker_alive_fn() or not event_q.empty():
        try:
            event_q.get(timeout=0.1)
        except queue.Empty:
            pass
