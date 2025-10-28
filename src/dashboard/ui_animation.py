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
