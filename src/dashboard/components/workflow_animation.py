"""
Workflow Animation Components (CSS/SVG-based)
A modern, reliable, and educational visualization of the PGx workflow.
"""
from __future__ import annotations

import streamlit as st
from typing import Optional, Dict, Any

# CSS once per session
_CSS_KEY = "_pgx_workflow_css_v1"


def _inject_css():
    if st.session_state.get(_CSS_KEY):
        return
    st.markdown(
        """
        <style>
        /* Container */
        .wf-wrap { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; background: #ffffff; }
        .wf-row { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
        .wf-stage { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px; border: 1px solid #e5e7eb; background: #f9fafb; transition: transform 180ms ease, box-shadow 180ms ease; }
        .wf-stage.active { background: #eef6ff; border-color: #bfdbfe; box-shadow: 0 2px 10px rgba(30, 64, 175, 0.08); }
        .wf-stage.done { background: #f0fdf4; border-color: #bbf7d0; }
        .wf-stage .label { font-weight: 600; font-size: 0.95rem; color: #0f172a; }
        .wf-stage .sub { font-size: 0.8rem; color: #475569; }
        .wf-pill { font-size: 0.75rem; padding: 2px 8px; background: #e2e8f0; color: #0f172a; border-radius: 999px; }
        .wf-counter { font-variant-numeric: tabular-nums; font-weight: 600; }

        /* Icons */
        .wf-ico { width: 28px; height: 28px; display: inline-block; }
        .wf-ico svg { width: 28px; height: 28px; }
        .wf-ico.dna path { stroke: #2563eb; }
        .wf-ico.tube rect { stroke: #0ea5e9; }
        .wf-ico.db path { stroke: #16a34a; }
        .wf-ico.pill path { stroke: #dc2626; }
        .wf-ico.doc path { stroke: #111827; }

        /* Progress bar */
        .wf-progress { height: 6px; background: #e5e7eb; border-radius: 999px; overflow: hidden; margin-top: 8px; }
        .wf-progress > div { height: 100%; width: 0%; background: linear-gradient(90deg,#60a5fa,#22d3ee); transition: width 220ms ease; }

        /* Tooltip */
        .wf-tip { position: relative; cursor: help; }
        .wf-tip .tip { position: absolute; z-index: 50; min-width: 220px; max-width: 300px; left: 0; top: 110%; background: #0f172a; color: #f8fafc; border-radius: 8px; padding: 10px 12px; font-size: 0.8rem; line-height: 1.2rem; display: none; box-shadow: 0 10px 30px rgba(0,0,0,0.15); }
        .wf-tip:hover .tip { display: block; }
        .wf-tip .tip b { color: #93c5fd; }

        /* Mini chips */
        .wf-chips { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
        .wf-chip { font-size: 0.7rem; padding: 2px 6px; background: #eff6ff; border: 1px solid #bfdbfe; color: #1e3a8a; border-radius: 6px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state[_CSS_KEY] = True


def _icon(name: str) -> str:
    # Simple inline SVGs for reliability
    if name == "tube":
        return """<span class='wf-ico tube'><svg viewBox='0 0 24 24' fill='none' stroke-width='1.8'>
        <rect x='7' y='3' width='10' height='4' rx='1.5' stroke='#0ea5e9'/>
        <path d='M9 7v10a3 3 0 0 0 6 0V7' stroke='#0ea5e9'/>
        <path d='M9 14h6' stroke='#38bdf8'/></svg></span>"""
    if name == "dna":
        return """<span class='wf-ico dna'><svg viewBox='0 0 24 24' fill='none' stroke-width='1.8'>
        <path d='M7 4c4 2 6 4 6 8s-2 6-6 8' stroke='#2563eb'/>
        <path d='M17 4c-4 2-6 4-6 8s2 6 6 8' stroke='#60a5fa'/>
        <path d='M8 7h8M8 12h8M8 17h8' stroke='#93c5fd'/></svg></span>"""
    if name == "db":
        return """<span class='wf-ico db'><svg viewBox='0 0 24 24' fill='none' stroke-width='1.8'>
        <ellipse cx='12' cy='6' rx='7' ry='3' stroke='#16a34a'/>
        <path d='M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6' stroke='#22c55e'/>
        <path d='M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3' stroke='#86efac'/></svg></span>"""
    if name == "pill":
        return """<span class='wf-ico pill'><svg viewBox='0 0 24 24' fill='none' stroke-width='1.8'>
        <path d='M7 12a5 5 0 0 1 10 0v0a5 5 0 0 1-10 0Z' stroke='#dc2626'/>
        <path d='M7 12l10 0' stroke='#f87171'/></svg></span>"""
    if name == "doc":
        return """<span class='wf-ico doc'><svg viewBox='0 0 24 24' fill='none' stroke-width='1.8'>
        <path d='M7 4h7l3 3v13H7z' stroke='#111827'/>
        <path d='M14 4v3h3' stroke='#6b7280'/>
        <path d='M9 10h6M9 13h6M9 16h6' stroke='#9ca3af'/></svg></span>"""
    return ""


class StoryboardV2:
    """CSS/SVG-based workflow storyboard with educational tooltips and live counters."""

    def __init__(self):
        _inject_css()
        self.progress = 0.0
        self.stage = "lab"
        self.state: Dict[str, Any] = {
            "variants": 0,
            "drugs": 0,
            "pubs": 0,
            "genes": [],
        }
        self._wrap = st.container()
        self.render("Initializing...")

    def set_genes(self, genes):
        self.state["genes"] = genes or []

    def render(self, caption: str = ""):
        with self._wrap:
            st.markdown("<div class='wf-wrap'>", unsafe_allow_html=True)
            # Row of stages
            cols = st.columns([1,1,1,1,1])
            stages = [
                ("lab", _icon("tube"), "Lab Prep", "Extracting DNA & QC"),
                ("ngs", _icon("dna"), "Sequencing", f"Variants: <span class='wf-counter'>{self.state['variants']}</span>"),
                ("anno", _icon("db"), "Annotation", f"Literature: <span class='wf-counter'>{self.state['pubs']}</span>"),
                ("drug", _icon("pill"), "Interactions", f"Drugs: <span class='wf-counter'>{self.state['drugs']}</span>"),
                ("report", _icon("doc"), "Report", "Compiling outputs"),
            ]
            order = ["lab","ngs","anno","drug","report"]
            current_index = order.index(self.stage) if self.stage in order else 0

            for i,(key, ico, title, sub) in enumerate(stages):
                cls = "wf-stage"
                if i < current_index:
                    cls += " done"
                elif i == current_index:
                    cls += " active"
                html = f"<div class='{cls}'>{ico}<div><div class='label'>{title}</div><div class='sub'>{sub}</div></div></div>"
                with cols[i]:
                    st.markdown(html, unsafe_allow_html=True)

            # Gene chips (optional)
            if self.state["genes"]:
                chips = "".join([f"<span class='wf-chip'>{g}</span>" for g in self.state["genes"][:10]])
                st.markdown(f"<div class='wf-chips'>{chips}</div>", unsafe_allow_html=True)

            # Progress
            st.markdown("<div class='wf-progress'><div style='width: %s%%'></div></div>" % int(self.progress*100), unsafe_allow_html=True)
            if caption:
                st.caption(caption)
            st.markdown("</div>", unsafe_allow_html=True)

    # Event-driven updates
    def advance(self, stage: str, message: str = "", progress: Optional[float] = None, deltas: Optional[Dict[str,int]] = None):
        if stage:
            self.stage = stage
        if progress is not None:
            self.progress = max(0.0, min(1.0, progress))
        if deltas:
            # Update counters safely
            for k,v in deltas.items():
                if k in self.state and isinstance(v, int):
                    try:
                        self.state[k] = max(0, int(self.state[k]) + int(v))
                    except Exception:
                        pass
        self.render(message)


# Convenience to consume EventBus-style events
def consume_events_v2(event_q, storyboard: StoryboardV2, worker_alive_fn):
    import queue
    while worker_alive_fn() or not event_q.empty():
        try:
            e = event_q.get(timeout=0.1)
            if not e:
                continue
            # Map old stages to new keys and adjust counters
            stage_map = {
                "lab_prep": "lab",
                "ngs": "ngs",
                "annotation": "anno",
                "enrichment": "drug",
                "linking": "drug",
                "report": "report",
            }
            deltas = {}
            # Heuristics: bump counters on certain substages/messages
            msg = getattr(e, 'message', '') or ''
            stg = stage_map.get(getattr(e, 'stage', ''), storyboard.stage)
            if stg == 'ngs' and any(w in msg.lower() for w in ["variant", "calling", "discovery"]):
                deltas['variants'] = 1
            if stg == 'anno' and any(w in msg.lower() for w in ["literature", "pmid", "europe pmc"]):
                deltas['pubs'] = 1
            if stg == 'drug' and any(w in msg.lower() for w in ["drug", "interaction", "recommendation"]):
                deltas['drugs'] = 1
            storyboard.advance(stage=stg, message=msg, progress=getattr(e, 'progress', None), deltas=deltas)
        except queue.Empty:
            pass
        except Exception:
            pass
