"""
Use the profile normalizer in PipelineWorker so dashboard profiles are passed to the pipeline in
canonical JSON-LD shape (foaf/schema) identical to generated ones.
"""
from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from ..main import PGxPipeline
    from .event_bus import PipelineEvent, EventBus
    from .profile_normalizer import normalize_dashboard_profile_to_jsonld
except Exception:
    import sys
    base = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(base))
    from main import PGxPipeline  # type: ignore
    from utils.event_bus import PipelineEvent, EventBus  # type: ignore
    from utils.profile_normalizer import normalize_dashboard_profile_to_jsonld  # type: ignore


class PipelineWorker(threading.Thread):
    """
    Dashboard-compatible Pipeline Worker that ensures patient_profile is always JSON-LD canonical.
    """

    def __init__(self, genes, profile=None, config_path="config.yaml", 
                 event_queue=None, result_queue=None, cancel_event=None, demo_mode=False):
        super().__init__(daemon=True)
        self.genes = genes
        self.raw_profile = profile or {}
        self.profile = normalize_dashboard_profile_to_jsonld(self.raw_profile) if profile else None
        self.config_path = config_path
        self.event_queue = event_queue or queue.Queue()
        self.result_queue = result_queue or queue.Queue()
        self.cancel_event = cancel_event or threading.Event()
        self.demo_mode = demo_mode

        self.event_bus = EventBus()
        self.event_bus.subscribe(self._forward_event)

        self.result = None
        self.error = None
        self.is_complete = False

    def _forward_event(self, e: PipelineEvent):
        try:
            self.event_queue.put(e)
        except Exception:
            pass

    def run(self):
        try:
            self._forward_event(PipelineEvent("lab_prep", "start", "Initializing pipeline...", 0.0))
            if self.demo_mode:
                self._run_demo()
            else:
                self._run_real()
            self._forward_event(PipelineEvent("report", "complete", "Analysis complete!", 1.0))
            if self.result:
                self.result_queue.put(self.result)
        except Exception as e:
            self.error = e
            self.result_queue.put({"success": False, "error": str(e)})
        finally:
            self.is_complete = True

    def _run_real(self):
        pipeline = PGxPipeline(config_path=self.config_path, event_bus=self.event_bus)
        out = pipeline.run_multi_gene(gene_symbols=self.genes, patient_profile=self.profile)
        if not out.get("success"):
            raise RuntimeError(out.get("error", "Pipeline failed"))
        self.result = {
            "success": True,
            "genes": out.get("genes", self.genes),
            "patient_id": out.get("patient_id"),
            "total_variants": out.get("total_variants", 0),
            "affected_drugs": out.get("affected_drugs", 0),
            "comprehensive_profile": out.get("comprehensive_profile"),
            "comprehensive_outputs": out.get("outputs", {})
        }

    def _run_demo(self):
        import time
        # Emit staged events
        stages = [
            ("lab_prep", "DNA extraction & QC", 0.15),
            ("ngs", "Sequencing & variant calling", 0.45),
            ("annotation", "Clinical annotation & literature", 0.7),
            ("enrichment", "Drug interactions & guidelines", 0.9),
        ]
        for s, msg, p in stages:
            if self.cancel_event.is_set():
                break
            self._forward_event(PipelineEvent(s, "processing", msg, p))
            time.sleep(0.6)

        # Build a demo result using the normalized profile envelope
        profile = self.profile or normalize_dashboard_profile_to_jsonld({})
        pid = profile.get("patient_id", "DEMO")
        profile["pharmacogenomics_profile"]["genes_analyzed"] = list(self.genes)
        profile["pharmacogenomics_profile"]["total_variants"] = 12
        profile["pharmacogenomics_profile"]["variants_by_gene"] = {g: 2 for g in self.genes}
        profile["pharmacogenomics_profile"]["affected_drugs"] = ["Warfarin", "Clopidogrel"]
        profile["pharmacogenomics_profile"]["associated_diseases"] = ["Drug toxicity"]

        # Minimal outputs (paths) for demo
        out_dir = Path("output/demo"); out_dir.mkdir(parents=True, exist_ok=True)
        import json
        jsonld_path = out_dir / f"{pid}_demo.jsonld"
        with open(jsonld_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2)

        self.result = {
            "success": True,
            "genes": list(self.genes),
            "patient_id": pid,
            "total_variants": 12,
            "affected_drugs": 2,
            "comprehensive_profile": profile,
            "comprehensive_outputs": {
                "Comprehensive JSON-LD": str(jsonld_path)
            }
        }


# Backwards-compat aliases
EnhancedBackgroundWorker = PipelineWorker
BackgroundWorker = PipelineWorker
