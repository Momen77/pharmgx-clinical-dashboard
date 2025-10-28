"""Streamlit UI helpers for the lab->NGS->report storyboard using Lottie."""
from __future__ import annotations

import queue
from dataclasses import asdict
from typing import Optional

import streamlit as st
from streamlit_lottie import st_lottie

# Fix import paths for direct execution
import sys
from pathlib import Path
dashboard_dir = Path(__file__).parent
src_dir = dashboard_dir.parent
sys.path.insert(0, str(src_dir))

from utils.lottie_loader import load_lottie_json
from utils.event_bus import PipelineEvent


class Storyboard:
    """Controls which Lottie scene is shown based on events."""

    def __init__(self) -> None:
        self.scene = "lab_prep"
        self.caption = "Preparing sample"
        self._place_anim = st.empty()
        self._place_text = st.empty()
        self._progress = st.progress(0)

        # Load assets lazily
        self.assets = {
            "lab_prep": load_lottie_json("lab_prep.json"),
            "ngs": load_lottie_json("ngs.json"),
            "bioinformatics": load_lottie_json("bioinformatics.json"),
            "report": load_lottie_json("report.json"),
        }

        self._render()

    def _render(self) -> None:
        anim = self.assets.get(self.scene, {})
        if not anim:
            # Fallback to placeholder if scene not found
            anim = load_lottie_json("placeholder.json")
        
        if anim:
            try:
                st_lottie(anim, height=240, key=f"anim_{self.scene}")
            except Exception:
                # Fallback to text if Lottie fails
                st.info(f"🎬 {self.scene.replace('_', ' ').title()}")
        self._place_text.info(self.caption)

    def advance(self, event: PipelineEvent) -> None:
        # Map stages to scenes
        if event.stage in {"lab_prep"}:
            self.scene = "lab_prep"
        elif event.stage in {"ngs"}:
            self.scene = "ngs"
        elif event.stage in {"annotation", "enrichment", "linking"}:
            self.scene = "bioinformatics"
        elif event.stage in {"report"}:
            self.scene = "report"

        self.caption = event.message
        if event.progress is not None:
            self._progress.progress(min(max(event.progress, 0), 1))

        self._render()


def consume_events(event_q: "queue.Queue", storyboard: Storyboard, worker_alive_fn) -> Optional[dict]:
    """Continuously consume events and update UI until done.

    Returns the result dict if one is received on a paired result queue
    managed by the outer caller; this function only drives the visuals.
    """
    log = st.container()
    with log:
        while worker_alive_fn() or not event_q.empty():
            try:
                e: PipelineEvent = event_q.get(timeout=0.1)
                storyboard.advance(e)
                st.write(f"[{e.stage}.{e.substage}] {e.message}")
            except queue.Empty:
                pass
    return None


