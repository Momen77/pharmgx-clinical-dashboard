"""
Replace Lottie storyboard with new CSS/SVG-based EnhancedStoryboardV2 (fixed names).
"""
from __future__ import annotations

import streamlit as st

# Import new components
try:
    from dashboard.components.workflow_animation import EnhancedStoryboardV2, consume_events_enhanced
except Exception:
    import importlib.util as _ilu
    from pathlib import Path as _P
    _p = _P(__file__).resolve().parent / "components" / "workflow_animation.py"
    if _p.exists():
        _s = _ilu.spec_from_file_location("workflow_animation", _p)
        _m = _ilu.module_from_spec(_s)
        _s.loader.exec_module(_m)  # type: ignore
        EnhancedStoryboardV2 = getattr(_m, "EnhancedStoryboardV2", None)
        consume_events_enhanced = getattr(_m, "consume_events_enhanced", None)
    else:
        EnhancedStoryboardV2 = None
        def consume_events_enhanced(*args, **kwargs):
            pass

# Backward-compatible API wrappers
class Storyboard:
    def __init__(self):
        self._sb = EnhancedStoryboardV2() if EnhancedStoryboardV2 else None

    def set_genes(self, genes):
        if self._sb and hasattr(self._sb, 'set_genes'):
            self._sb.set_genes(genes)

    def advance(self, event):
        if not self._sb or not event:
            return
        # Map fields
        stage = getattr(event, 'stage', None)
        msg = getattr(event, 'message', '')
        prog = getattr(event, 'progress', None)
        self._sb.advance(stage=stage, message=msg, progress=prog)

    def set_demo_plan(self, plan, speed_ms: int = 800):
        """Expose demo plan to app.py for smooth client-side animation."""
        if self._sb and hasattr(self._sb, 'set_demo_plan'):
            self._sb.set_demo_plan(plan, speed_ms)
    
    def render(self, caption: str = ""):
        if self._sb and hasattr(self._sb, 'render'):
            self._sb.render(caption)


def consume_events(event_q, storyboard: Storyboard, worker_alive_fn):
    if hasattr(storyboard, '_sb') and storyboard._sb and consume_events_enhanced:
        return consume_events_enhanced(event_q, storyboard._sb, worker_alive_fn)
    # Fallback: no-op loop to keep UI responsive
    import queue
    while worker_alive_fn() or not event_q.empty():
        try:
            _ = event_q.get(timeout=0.1)
        except queue.Empty:
            pass


def create_storyboard_with_controls():
    """Debug helper to render EnhancedStoryboardV2 with minimal controls.

    Returns the underlying EnhancedStoryboardV2 instance for external use.
    """
    if not EnhancedStoryboardV2:
        st.info("Enhanced storyboard component not available")
        return None

    # Force CSS injection and initial render
    sb = EnhancedStoryboardV2()
    sb.render("Storyboard initialized")

    # Minimal controls for debug page
    st.markdown("### Storyboard Controls")
    genes = st.text_input("Genes (comma-separated)", value="CYP2D6,CYP2C19,TPMT,DPYD")
    if genes:
        sb.set_genes([g.strip() for g in genes.split(',') if g.strip()])

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Stage: lab_prep"):
            sb.advance(stage="lab_prep", message="Initializing...", progress=0.05)
    with col2:
        if st.button("Stage: ngs"):
            sb.advance(stage="ngs", message="Sequencing...", progress=0.3)
    with col3:
        if st.button("Stage: annotation"):
            sb.advance(stage="annotation", message="Annotating...", progress=0.5)

    col4, col5, col6 = st.columns(3)
    with col4:
        if st.button("Stage: enrichment"):
            sb.advance(stage="enrichment", message="Enriching...", progress=0.7)
    with col5:
        if st.button("Stage: linking"):
            sb.advance(stage="linking", message="Linking...", progress=0.85)
    with col6:
        if st.button("Stage: report"):
            sb.advance(stage="report", message="Generating reports...", progress=0.95)

    # Explicit re-render button for environments that delay initial HTML draw
    if st.button("🔁 Re-render storyboard"):
        sb.render("Manual refresh")

    return sb