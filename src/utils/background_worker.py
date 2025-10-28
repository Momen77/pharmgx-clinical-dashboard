"""
Background worker that executes the PGx pipeline and emits UI events.
"""
from __future__ import annotations

import threading
import queue
from typing import Any, Dict, List, Optional

from pathlib import Path
import sys

# Local imports
from .event_bus import emit


class PipelineWorker(threading.Thread):
    """Run the existing pipeline while emitting detailed events."""

    def __init__(self, genes: List[str], profile: Dict[str, Any], config_path: str,
                 event_queue: "queue.Queue", result_queue: "queue.Queue",
                 cancel_event: Optional[threading.Event] = None,
                 demo_mode: bool = False) -> None:
        super().__init__(daemon=True)
        self.genes = genes
        self.profile = profile
        self.config_path = config_path
        self.event_queue = event_queue
        self.result_queue = result_queue
        self.cancel_event = cancel_event or threading.Event()
        self.demo_mode = demo_mode

        # Ensure src on path to import pipeline
        project_root = Path(__file__).resolve().parents[3]
        src_dir = project_root / "src" / "pharmgx-clinical-dashboard" / "src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

        try:
            from main import PGxKGPipeline  # type: ignore
        except Exception:
            from src.main import PGxKGPipeline  # type: ignore
        self.PGxKGPipeline = PGxKGPipeline

    def run(self) -> None:
        emit(self.event_queue, "lab_prep", "accession", "Sample received and accessioned")
        emit(self.event_queue, "lab_prep", "barcode", "Applying barcode and preparing library", progress=0.05)
        emit(self.event_queue, "lab_prep", "library_prep", "Library prep complete", progress=0.10)

        emit(self.event_queue, "ngs", "flowcell", "Loading flowcell and starting sequencing", progress=0.15)
        for cycle in range(1, 6):
            if self.cancel_event.is_set():
                emit(self.event_queue, "report", "cancelled", "Run cancelled", level="warning")
                return
            emit(self.event_queue, "ngs", f"cycle_{cycle}", f"Sequencing cycle {cycle}/5", progress=0.15 + cycle * 0.05)

        emit(self.event_queue, "ngs", "basecalling", "Performing basecalling", progress=0.45)
        emit(self.event_queue, "ngs", "alignment", "Aligning reads to reference", progress=0.55)
        emit(self.event_queue, "ngs", "variant_calling", "Calling variants", progress=0.65)

        # Execute actual pipeline
        try:
            if self.demo_mode:
                # Simulated result
                emit(self.event_queue, "annotation", "uniprot_connect", "Connecting to UniProt API…", progress=0.70)
                emit(self.event_queue, "annotation", "pharmgkb_connect", "Connecting to PharmGKB…")
                emit(self.event_queue, "enrichment", "chembl_connect", "Connecting to ChEMBL…")
                emit(self.event_queue, "enrichment", "europepmc_connect", "Querying Europe PMC for literature…")
                results = {
                    "success": True,
                    "genes": self.genes,
                    "total_variants": 12,
                    "affected_drugs": 7,
                    "associated_diseases": 5,
                    "comprehensive_outputs": {}
                }
            else:
                pipeline = self.PGxKGPipeline(config_path=self.config_path)
                emit(self.event_queue, "annotation", "uniprot_connect", "Connecting to UniProt API…", progress=0.70)
                emit(self.event_queue, "annotation", "pharmgkb_connect", "Connecting to PharmGKB…")
                emit(self.event_queue, "enrichment", "chembl_connect", "Connecting to ChEMBL…")
                emit(self.event_queue, "enrichment", "europepmc_connect", "Querying Europe PMC for literature…")
                results = pipeline.run_multi_gene(self.genes)

            emit(self.event_queue, "linking", "link_variants", "Linking variants to conditions & drugs", progress=0.85)
            emit(self.event_queue, "report", "generate", "Generating JSON-LD and HTML report", progress=0.95)

            self.result_queue.put(results)
            emit(self.event_queue, "report", "complete", "Pipeline complete", level="success", progress=1.0)
        except Exception as exc:
            self.result_queue.put({"success": False, "error": str(exc)})
            emit(self.event_queue, "report", "error", f"Pipeline failed: {exc}", level="error")


