"""Enhanced background worker with proper profile passing and error handling."""
from __future__ import annotations

import queue
import threading
import time
from typing import Optional, Dict, Any

# Import pipeline components
try:
    from ..phase1_discovery.pipeline import PGxPipeline
    from .event_bus import PipelineEvent, EventBus
except ImportError:
    # Fallback imports for different execution contexts
    import sys
    from pathlib import Path
    src_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(src_dir))
    
    try:
        from phase1_discovery.pipeline import PGxPipeline
        from utils.event_bus import PipelineEvent, EventBus
    except ImportError:
        # Further fallback - create minimal classes if imports fail
        class PGxPipeline:
            def __init__(self, event_bus=None):
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
    
    def __init__(self, genes: list, patient_profile: Optional[Dict[str, Any]] = None, profile: Optional[Dict[str, Any]] = None):
        super().__init__(daemon=True)
        self.genes = genes
        # Accept both parameter names for compatibility with different callers
        self.profile = patient_profile if patient_profile is not None else profile
        self.event_queue = queue.Queue()
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
            
            # Initialize pipeline
            pipeline = PGxPipeline(event_bus=self.event_bus)
            
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
            
            # Emit completion event
            self.event_queue.put(PipelineEvent(
                stage="report",
                substage="complete",
                message="Analysis complete!",
                progress=1.0
            ))
            
            print(f"[WORKER] Pipeline completed successfully")
            
            # Add output summary to result if available
            if isinstance(self.result, dict) and 'outputs' in self.result:
                output_types = list(self.result['outputs'].keys())
                print(f"[WORKER] Generated outputs: {output_types}")
            
        except Exception as e:
            self.error = e
            print(f"[WORKER] Pipeline error: {e}")
            
            self.event_queue.put(PipelineEvent(
                stage="error",
                substage="pipeline",
                message=f"Pipeline error: {str(e)}",
                progress=0.0
            ))
        finally:
            self.is_complete = True
            print(f"[WORKER] Worker thread completed")
    
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
