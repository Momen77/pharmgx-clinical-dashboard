"""
Replace Lottie storyboard with new CSS/SVG-based StoryboardV2.
"""
from __future__ import annotations

import streamlit as st

# Import new components
try:
    from dashboard.components.workflow_animation import StoryboardV2, consume_events_v2
except Exception:
    import importlib.util as _ilu
    from pathlib import Path as _P
    _p = _P(__file__).resolve().parent / "components" / "workflow_animation.py"
    if _p.exists():
        _s = _ilu.spec_from_file_location("workflow_animation", _p)
        _m = _ilu.module_from_spec(_s)
        _s.loader.exec_module(_m)  # type: ignore
        StoryboardV2 = _m.StoryboardV2
        consume_events_v2 = _m.consume_events_v2
    else:
        StoryboardV2 = None
        def consume_events_v2(*args, **kwargs):
            pass

# Backward-compatible API wrappers
class Storyboard:
    def __init__(self):
        self._sb = StoryboardV2() if StoryboardV2 else None

    def advance(self, event):
        if not self._sb or not event:
            return
        # Minimal adapter: map fields
        stage = getattr(event, 'stage', None)
        msg = getattr(event, 'message', '')
        prog = getattr(event, 'progress', None)
        self._sb.advance(stage=stage, message=msg, progress=prog)


def consume_events(event_q, storyboard: Storyboard, worker_alive_fn):
    if hasattr(storyboard, '_sb') and storyboard._sb:
        return consume_events_v2(event_q, storyboard._sb, worker_alive_fn)
    # Fallback: no-op
    import queue
    while worker_alive_fn() or not event_q.empty():
        try:
            _ = event_q.get(timeout=0.1)
        except queue.Empty:
            pass
