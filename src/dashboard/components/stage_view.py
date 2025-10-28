"""
Update EnhancedStoryboardV2 to show only the active stage expanded.
Other stages render as compact headers without details, microsteps, or extras.
"""
from __future__ import annotations

import streamlit as st
from typing import Optional, Dict, Any, List

try:
    from .workflow_details import DETAIL_SCRIPTS
except Exception:
    DETAIL_SCRIPTS = {}

# Flags stored in session to avoid flashing
_FLAG_KEY = "_pgx_storyboard_compact_mode_v1"


def _ensure_flag():
    if _FLAG_KEY not in st.session_state:
        st.session_state[_FLAG_KEY] = True


def stage_order_list():
    return ["lab", "ngs", "anno", "drug", "report"]


def stage_title_subtitle(state: Dict[str, Any]):
    return [
        ("lab", "🧪", "Lab Prep", "DNA extraction & library prep"),
        ("ngs", "🧬", "Sequencing", f"Variants: {state.get('variants', 0)}"),
        ("anno", "🔬", "Annotation", f"Literature: {state.get('literature', 0)}"),
        ("drug", "💊", "Interactions", f"Drugs: {state.get('drugs', 0)}"),
        ("report", "📊", "Report", "Comprehensive results"),
    ]


def render_compact_stage(icon: str, title: str, subtitle: str, done: bool, active: bool) -> str:
    base = "wf-stage"
    if active:
        base += " active"
    elif done:
        base += " done"
    # Compact layout: no microsteps and minimal details
    return f"""
    <div class='{base}'>
      <div class='wf-stage-icon'>{icon}</div>
      <div class='wf-stage-title'>{title}</div>
      <div class='wf-stage-detail'>{subtitle}</div>
    </div>
    """


def render_expanded_stage(stage_id: str, icon: str, title: str, subtitle: str, state: Dict[str, Any]) -> str:
    # Expanded layout: includes microsteps and any stage-specific content
    html = f"""
    <div class='wf-stage active'>
      <div class='wf-stage-icon'>{icon}</div>
      <div class='wf-stage-title'>{title}</div>
      <div class='wf-stage-detail'>{subtitle}</div>
    """
    # Microsteps
    steps = DETAIL_SCRIPTS.get(stage_id, [])
    if steps:
        html += "<div class='wf-microsteps'>"
        # Determine current microstep from state
        current = int(state.get('microstep', 0))
        for i, step in enumerate(steps):
            cls = "wf-microstep"
            if i < current:
                cls += " done"
            elif i == current:
                cls += " active"
            html += f"""
            <div class='{cls}'>
              <span class='wf-microstep-icon'></span>
              <span title='{step.get('hint','')}'>{step.get('label','')}</span>
            </div>
            """
        html += "</div>"
    # Stage-specific extras are omitted here; ui component injects them
    html += "</div>"
    return html


def clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


class StageViewController:
    """Controller to enforce only active stage expanded."""

    def __init__(self):
        _ensure_flag()
        self.order = stage_order_list()

    def render(self, container, active_stage: str, state: Dict[str, Any]):
        with container:
            st.markdown("<div class='wf-stages'>", unsafe_allow_html=True)
            titles = stage_title_subtitle(state)
            cur_idx = self.order.index(active_stage) if active_stage in self.order else 0
            for i, (sid, icon, title, subtitle) in enumerate(titles):
                if i == cur_idx:
                    st.markdown(render_expanded_stage(sid, icon, title, subtitle, state), unsafe_allow_html=True)
                else:
                    st.markdown(render_compact_stage(icon, title, subtitle, done=i < cur_idx, active=False), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)


class AnimatedProgress:
    @staticmethod
    def render(progress: float):
        progress = clamp(progress)
        st.markdown(
            f"""
            <div class='wf-progress'>
              <div class='wf-progress-fill' style='width: {int(progress*100)}%'></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
