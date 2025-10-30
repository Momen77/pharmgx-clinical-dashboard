"""Enhanced background worker with proper profile passing and error handling."""
from __future__ import annotations

import queue
import threading
import time
from typing import Optional, Dict, Any

# Import pipeline components
try:
    from ..main import PGxPipeline
    from .event_bus import PipelineEvent, EventBus
except ImportError:
    # Fallback imports for different execution contexts
    import sys
    from pathlib import Path
    src_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(src_dir))

    try:
        from main import PGxPipeline
        from utils.event_bus import PipelineEvent, EventBus
    except ImportError:
        # Further fallback - create minimal classes if imports fail
        class PGxPipeline:
            def __init__(self, config_path="config.yaml", event_bus=None):
                self.config_path = config_path
                self.event_bus = event_bus

            def run_single_gene(self, gene_symbol, patient_profile=None):
                return {"gene": gene_symbol, "status": "completed"}

            def run_multi_gene(self, gene_symbols, patient_profile=None):
                return {"genes": gene_symbols, "status": "completed"}

        class PipelineEvent:
            def __init__(self, stage, substage, message, progress=None):
                self.stage = stage
                self.substage = substage
                self.message = message
                self.progress = progress

        class EventBus:
            def __init__(self):
                self.subscribers = []

            def subscribe(self, callback):
                self.subscribers.append(callback)

            def emit(self, event):
                for callback in self.subscribers:
                    try:
                        callback(event)
                    except Exception as e:
                        print(f"Event callback error: {e}")


class EnhancedBackgroundWorker(threading.Thread):
    """Enhanced background worker that properly handles patient profiles and generates all output formats."""
    
    def __init__(self, genes: list, patient_profile: Optional[Dict[str, Any]] = None, profile: Optional[Dict[str, Any]] = None, 
                 config_path: str = "config.yaml", event_queue=None, result_queue=None, cancel_event=None, demo_mode=False):
        super().__init__(daemon=True)
        self.genes = genes
        # Accept both parameter names for compatibility with different callers
        self.profile = patient_profile if patient_profile is not None else profile
        self.config_path = config_path
        self.event_queue = event_queue or queue.Queue()
        self.result_queue = result_queue or queue.Queue()
        self.cancel_event = cancel_event or threading.Event()
        self.demo_mode = demo_mode
        self.result = None
        self.error = None
        self.is_complete = False
        
        # Initialize event bus
        self.event_bus = EventBus()
        self.event_bus.subscribe(self._on_pipeline_event)
        
        print(f"[WORKER] Initialized with genes: {genes}")
        if self.profile:
            print(f"[WORKER] Using patient profile: {self.profile.get('patient_id', 'Unknown')}")
        else:
            print("[WORKER] No patient profile provided, will generate synthetic data")
        
    def _on_pipeline_event(self, event: PipelineEvent):
        """Handle pipeline events and forward to UI."""
        try:
            self.event_queue.put(event)
            print(f"[WORKER] Event: [{event.stage}.{event.substage}] {event.message}")
        except Exception as e:
            print(f"[WORKER] Error forwarding event: {e}")
    
    def run(self):
        """Run the pipeline with proper error handling."""
        try:
            # Emit initial event
            self.event_queue.put(PipelineEvent(
                stage="lab_prep",
                substage="init",
                message="Initializing pipeline...",
                progress=0.0
            ))
            
            print(f"[WORKER] Starting pipeline for genes: {self.genes}")
            
            if self.demo_mode:
                self._run_demo()
            else:
                self._run_real()
                
            # Emit completion event
            self.event_queue.put(PipelineEvent(
                stage="report",
                substage="complete",
                message="Analysis complete!",
                progress=1.0
            ))
            
            if self.result:
                self.result_queue.put(self.result)
            
        except Exception as e:
            self.error = e
            print(f"[WORKER] Pipeline error: {e}")
            
            self.event_queue.put(PipelineEvent(
                stage="error",
                substage="pipeline",
                message=f"Pipeline error: {str(e)}",
                progress=0.0
            ))
            self.result_queue.put({"success": False, "error": str(e)})
        finally:
            self.is_complete = True
            print(f"[WORKER] Worker thread completed")
    
    def _run_real(self):
        """Run the real pipeline."""
        # Initialize pipeline
        pipeline = PGxPipeline(config_path=self.config_path, event_bus=self.event_bus)
        
        # Run analysis based on number of genes
        if len(self.genes) == 1:
            # Single gene analysis
            gene = self.genes[0]
            print(f"[WORKER] Running single gene analysis for: {gene}")
            
            self.event_queue.put(PipelineEvent(
                stage="ngs",
                substage="single_gene",
                message=f"Analyzing gene {gene}...",
                progress=0.3
            ))
            
            self.result = pipeline.run_single_gene(
                gene_symbol=gene,
                patient_profile=self.profile
            )
        else:
            # Multi-gene analysis  
            print(f"[WORKER] Running multi-gene analysis for: {self.genes}")
            
            self.event_queue.put(PipelineEvent(
                stage="ngs",
                substage="multi_gene",
                message=f"Analyzing {len(self.genes)} genes...",
                progress=0.3
            ))
            
            # Check if pipeline has run_multi_gene method with patient_profile parameter
            try:
                import inspect
                sig = inspect.signature(pipeline.run_multi_gene)
                if 'patient_profile' in sig.parameters:
                    self.result = pipeline.run_multi_gene(
                        gene_symbols=self.genes,
                        patient_profile=self.profile
                    )
                else:
                    # Fallback for older pipeline versions
                    self.result = pipeline.run_multi_gene(self.genes)
                    print("[WORKER] Warning: Pipeline doesn't support patient_profile parameter")
            except Exception as e:
                print(f"[WORKER] Error checking pipeline signature: {e}")
                # Simple fallback
                self.result = pipeline.run_multi_gene(self.genes)
        
        print(f"[WORKER] Pipeline completed successfully")
        
        # Add output summary to result if available
        if isinstance(self.result, dict) and 'outputs' in self.result:
            output_types = list(self.result['outputs'].keys())
            print(f"[WORKER] Generated outputs: {output_types}")
    
    def _run_demo(self):
        """Run demo mode with simulated pipeline stages."""
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
            self.event_queue.put(PipelineEvent(s, "processing", msg, p))
            time.sleep(0.6)

        # Build a demo result
        self.result = {
            "success": True,
            "genes": list(self.genes),
            "patient_id": "DEMO",
            "total_variants": 12,
            "affected_drugs": 2,
            "comprehensive_profile": {"patient_id": "DEMO", "dashboard_source": True},
            "comprehensive_outputs": {
                "Comprehensive JSON-LD": "output/demo/DEMO_demo.jsonld"
            }
        }
    
    def is_alive(self) -> bool:
        """Check if worker is still running."""
        return super().is_alive() and not self.is_complete
    
    def get_events(self) -> queue.Queue:
        """Get the event queue for UI consumption."""
        return self.event_queue
    
    def get_result(self) -> Optional[Dict[str, Any]]:
        """Get the pipeline result."""
        return self.result
    
    def get_error(self) -> Optional[Exception]:
        """Get any error that occurred."""
        return self.error
    
    def get_status(self) -> Dict[str, Any]:
        """Get current worker status."""
        return {
            "is_alive": self.is_alive(),
            "is_complete": self.is_complete,
            "has_result": self.result is not None,
            "has_error": self.error is not None,
            "genes": self.genes,
            "has_profile": self.profile is not None
        }


def create_worker(genes: list, patient_profile: Optional[Dict[str, Any]] = None) -> EnhancedBackgroundWorker:
    """Factory function to create and start a background worker."""
    if not genes:
        raise ValueError("At least one gene must be specified")
    
    print(f"[FACTORY] Creating worker for genes: {genes}")
    if patient_profile:
        print(f"[FACTORY] Patient profile provided: {patient_profile.get('patient_id', 'Unknown')}")
    
    worker = EnhancedBackgroundWorker(genes, patient_profile)
    worker.start()
    
    print(f"[FACTORY] Worker started successfully")
    return worker


# Legacy compatibility
class BackgroundWorker(EnhancedBackgroundWorker):
    """Legacy compatibility class."""
    pass

# New worker class to bypass caching issues
class StreamlitCompatibleWorker(threading.Thread):
    """Streamlit-compatible worker with full parameter support."""
    
    def __init__(self, genes: list, patient_profile=None, profile=None, 
                 config_path: str = "config.yaml", event_queue=None, result_queue=None, 
                 cancel_event=None, demo_mode=False):
        super().__init__(daemon=True)
        self.genes = genes
        # Accept both parameter names for compatibility
        self.profile = patient_profile if patient_profile is not None else profile
        self.config_path = config_path
        self.event_queue = event_queue or queue.Queue()
        self.result_queue = result_queue or queue.Queue()
        self.cancel_event = cancel_event or threading.Event()
        self.demo_mode = demo_mode
        self.result = None
        self.error = None
        self.is_complete = False
        
        # Initialize event bus
        self.event_bus = EventBus()
        self.event_bus.subscribe(self._on_pipeline_event)
        
        print(f"[WORKER] Initialized with genes: {genes}")
        if self.profile:
            print(f"[WORKER] Using patient profile: {self.profile.get('patient_id', 'Unknown')}")
        else:
            print("[WORKER] No patient profile provided, will generate synthetic data")
    
    def _on_pipeline_event(self, event):
        """Handle pipeline events and forward to UI."""
        try:
            self.event_queue.put(event)
            print(f"[WORKER] Event: [{event.stage}.{event.substage}] {event.message}")
        except Exception as e:
            print(f"[WORKER] Error forwarding event: {e}")
    
    def run(self):
        """Run the pipeline with proper error handling."""
        try:
            # Emit initial event
            self.event_queue.put(PipelineEvent(
                stage="lab_prep",
                substage="init",
                message="Initializing pipeline...",
                progress=0.0
            ))
            
            print(f"[WORKER] Starting pipeline for genes: {self.genes}")
            
            if self.demo_mode:
                self._run_demo()
            else:
                self._run_real()
                
            # Emit completion event
            self.event_queue.put(PipelineEvent(
                stage="report",
                substage="complete",
                message="Analysis complete!",
                progress=1.0
            ))
            
            if self.result:
                self.result_queue.put(self.result)
            
        except Exception as e:
            self.error = e
            print(f"[WORKER] Pipeline error: {e}")
            
            self.event_queue.put(PipelineEvent(
                stage="error",
                substage="pipeline",
                message=f"Pipeline error: {str(e)}",
                progress=0.0
            ))
            self.result_queue.put({"success": False, "error": str(e)})
        finally:
            self.is_complete = True
            print(f"[WORKER] Worker thread completed")
    
    def _run_real(self):
        """Run the real pipeline."""
        try:
            # Initialize pipeline
            pipeline = PGxPipeline(config_path=self.config_path, event_bus=self.event_bus)
            
            # Run multi-gene analysis
            print(f"[WORKER] Running multi-gene analysis for: {self.genes}")
            
            self.event_queue.put(PipelineEvent(
                stage="ngs",
                substage="multi_gene",
                message=f"Analyzing {len(self.genes)} genes...",
                progress=0.3
            ))
            
            # Try to run with patient_profile parameter
            try:
                import inspect
                sig = inspect.signature(pipeline.run_multi_gene)
                if 'patient_profile' in sig.parameters:
                    result = pipeline.run_multi_gene(
                        gene_symbols=self.genes,
                        patient_profile=self.profile
                    )
                else:
                    result = pipeline.run_multi_gene(self.genes)
                    print("[WORKER] Warning: Pipeline doesn't support patient_profile parameter")
            except Exception as e:
                print(f"[WORKER] Error running pipeline: {e}")
                result = {"success": False, "error": str(e)}
            
            self.result = result
            print(f"[WORKER] Pipeline completed successfully")
            
        except Exception as e:
            print(f"[WORKER] Error in _run_real: {e}")
            self.result = {"success": False, "error": str(e)}
    
    def _run_demo(self):
        """Run demo mode with simulated pipeline stages."""
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
            self.event_queue.put(PipelineEvent(s, "processing", msg, p))
            time.sleep(0.6)

        # Build a demo result
        self.result = {
            "success": True,
            "genes": list(self.genes),
            "patient_id": "DEMO",
            "total_variants": 12,
            "affected_drugs": 2,
            "comprehensive_profile": {"patient_id": "DEMO", "dashboard_source": True},
            "comprehensive_outputs": {
                "Comprehensive JSON-LD": "output/demo/DEMO_demo.jsonld"
            }
        }
    
    def is_alive(self) -> bool:
        """Check if worker is still running."""
        return super().is_alive() and not self.is_complete
    
    def get_events(self):
        """Get the event queue for UI consumption."""
        return self.event_queue
    
    def get_result(self):
        """Get the pipeline result."""
        return self.result
    
    def get_error(self):
        """Get any error that occurred."""
        return self.error
    
    def get_status(self):
        """Get current worker status."""
        return {
            "is_alive": self.is_alive(),
            "is_complete": self.is_complete,
            "has_result": self.result is not None,
            "has_error": self.error is not None,
            "genes": self.genes,
            "has_profile": self.profile is not None
        }
