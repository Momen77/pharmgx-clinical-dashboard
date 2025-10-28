"""Streamlit UI helpers for the lab->NGS->report storyboard using Lottie with robust asset loading."""
from __future__ import annotations

import queue
from typing import Optional, Dict
import streamlit as st
from streamlit_lottie import st_lottie

# Fix import paths for Streamlit execution
import sys
from pathlib import Path

# Add src directory to path for imports
dashboard_dir = Path(__file__).parent
src_dir = dashboard_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

try:
    from utils.lottie_loader import load_lottie_json, load_all_lottie_assets, get_asset_or_fallback
    from utils.event_bus import PipelineEvent
except ImportError:
    # Fallback for different execution contexts
    import importlib.util
    
    lottie_path = src_dir / "utils" / "lottie_loader.py"
    if lottie_path.exists():
        spec = importlib.util.spec_from_file_location("lottie_loader", lottie_path)
        lottie_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lottie_module)
        load_lottie_json = lottie_module.load_lottie_json
        load_all_lottie_assets = getattr(lottie_module, 'load_all_lottie_assets', lambda: {})
        get_asset_or_fallback = getattr(lottie_module, 'get_asset_or_fallback', lambda s, a: {})
    
    event_path = src_dir / "utils" / "event_bus.py"
    if event_path.exists():
        spec = importlib.util.spec_from_file_location("event_bus", event_path)
        event_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(event_module)
        PipelineEvent = event_module.PipelineEvent


class Storyboard:
    """Controls which Lottie scene is shown based on events."""

    def __init__(self) -> None:
        self.scene = "lab_prep"
        self.caption = "Preparing sample"
        self._place_anim = st.empty()
        self._place_text = st.empty()
        self._progress = st.progress(0)
        self._render_count = 0  # ensure unique widget keys per render

        # Load all assets at once with improved error handling
        st.info("🔄 Loading animation assets...")
        self.assets = load_all_lottie_assets()
        
        # Display loading status for each asset
        asset_status = []
        for scene_name in ["lab_prep", "ngs", "bioinformatics", "report"]:
            if scene_name in self.assets and self.assets[scene_name]:
                asset_status.append(f"✅ {scene_name}.json")
            else:
                asset_status.append(f"❌ {scene_name}.json")
        
        # Show status in a more compact way
        status_cols = st.columns(len(asset_status))
        for i, status in enumerate(asset_status):
            with status_cols[i]:
                if "✅" in status:
                    st.success(status, icon="✅")
                else:
                    st.error(status, icon="❌")

        self._render()

    def _render(self) -> None:
        """Render the current scene with improved error handling."""
        # Clear previous animation to avoid duplicate widget keys
        self._place_anim.empty()
        self._render_count += 1
        
        # Get the asset for current scene with fallback
        anim = get_asset_or_fallback(self.scene, self.assets)
        used_asset = f"{self.scene}.json" if (self.scene in self.assets and self.assets[self.scene]) else "fallback"
        
        # Render animation or fallback
        with self._place_anim.container():
            if anim and len(anim.get("layers", [])) > 0:
                try:
                    st_lottie(
                        anim,
                        height=240,
                        loop=True,
                        quality="high",
                        key=f"anim_{self.scene}_{self._render_count}"
                    )
                except Exception as e:
                    # Fallback to emoji representation
                    scene_emojis = {
                        "lab_prep": "🧪",
                        "ngs": "🧬",
                        "bioinformatics": "💻",
                        "report": "📊"
                    }
                    emoji = scene_emojis.get(self.scene, "⚙️")
                    st.markdown(f"""
                    <div style="text-align: center; padding: 40px;">
                        <div style="font-size: 4em;">{emoji}</div>
                        <div style="font-size: 1.2em; margin-top: 10px;">{self.scene.replace('_', ' ').title()}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.error(f"Animation error: {e}")
            else:
                # Emoji fallback for missing animations
                scene_emojis = {
                    "lab_prep": "🧪",
                    "ngs": "🧬", 
                    "bioinformatics": "💻",
                    "report": "📊"
                }
                emoji = scene_emojis.get(self.scene, "⚙️")
                st.markdown(f"""
                <div style="text-align: center; padding: 40px;">
                    <div style="font-size: 4em;">{emoji}</div>
                    <div style="font-size: 1.2em; margin-top: 10px;">{self.scene.replace('_', ' ').title()}</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Show caption with asset info
        self._place_text.info(f"{self.caption}  ·  asset: {used_asset}")

    def advance(self, event: PipelineEvent) -> None:
        """Advance to next scene based on pipeline event."""
        # Safety check for event
        if event is None:
            return
            
        # Map stages to scenes with more granular mapping
        stage_to_scene = {
            "lab_prep": "lab_prep",
            "ngs": "ngs",  
            "annotation": "bioinformatics",
            "enrichment": "bioinformatics",
            "linking": "bioinformatics",
            "report": "report",
            "export": "report"
        }
        
        new_scene = stage_to_scene.get(event.stage, self.scene)
        if new_scene != self.scene:
            self.scene = new_scene
            
        self.caption = event.message if event.message else "Processing..."
        
        # Update progress bar
        if event.progress is not None:
            progress_val = min(max(event.progress, 0), 1)
            self._progress.progress(progress_val)

        self._render()

    def set_scene(self, scene_name: str, caption: str = None):
        """Manually set the scene (useful for testing or direct control)."""
        if scene_name in ["lab_prep", "ngs", "bioinformatics", "report"]:
            self.scene = scene_name
            if caption:
                self.caption = caption
            self._render()


def consume_events(event_q: "queue.Queue", storyboard: Storyboard, worker_alive_fn) -> Optional[dict]:
    """Continuously consume events and update UI until done.

    Returns the result dict if one is received on a paired result queue
    managed by the outer caller; this function only drives the visuals.
    """
    log = st.container()
    event_count = 0
    
    with log:
        while worker_alive_fn() or not event_q.empty():
            try:
                e = event_q.get(timeout=0.1)
                if e is None:
                    continue
                    
                event_count += 1
                storyboard.advance(e)
                
                # Show event log with better formatting
                with st.expander(f"Event Log ({event_count} events)", expanded=False):
                    st.write(f"**[{e.stage}.{e.substage}]** {e.message}")
                    if hasattr(e, 'progress') and e.progress is not None:
                        st.write(f"Progress: {e.progress:.1%}")
                        
            except queue.Empty:
                pass
            except Exception as ex:
                st.error(f"Event processing error: {ex}")
                
    return None


def create_storyboard_with_controls() -> Storyboard:
    """Create a storyboard with manual controls for testing."""
    storyboard = Storyboard()
    
    # Add manual controls in sidebar for testing
    with st.sidebar:
        st.subheader("Animation Controls")
        
        scene_options = ["lab_prep", "ngs", "bioinformatics", "report"]
        selected_scene = st.selectbox("Manual Scene Selection", scene_options, 
                                    index=scene_options.index(storyboard.scene))
        
        custom_caption = st.text_input("Custom Caption", storyboard.caption)
        
        if st.button("Update Scene"):
            storyboard.set_scene(selected_scene, custom_caption)
    
    return storyboard
