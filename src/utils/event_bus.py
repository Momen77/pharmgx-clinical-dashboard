"""
Event bus utilities for dashboard → pipeline communication.

Provides a simple dataclass for pipeline events and helper functions to
emit events into a thread-safe Queue. Designed to be lightweight and to
avoid introducing heavy dependencies.
"""
from typing import Any, Dict, Optional


class PipelineEvent:
    """Simple event class for pipeline communication."""
    
    def __init__(self, stage: str, substage: str, level: str, message: str,
                 progress: Optional[float] = None, payload: Optional[Dict[str, Any]] = None):
        self.stage = stage or "unknown"
        self.substage = substage or "unknown"
        self.level = level or "info"
        self.message = message or "No message"
        self.progress = progress
        self.payload = payload


def emit(event_queue, stage: str, substage: str, message: str,
         level: str = "info", progress: Optional[float] = None,
         payload: Optional[Dict[str, Any]] = None) -> None:
    """Put a PipelineEvent into the provided queue."""
    try:
        # Safety checks for parameters
        if event_queue is None:
            return
            
        # Create the event with explicit parameters
        event = PipelineEvent(
            stage=str(stage) if stage else "unknown", 
            substage=str(substage) if substage else "unknown", 
            level=str(level) if level else "info",
            message=str(message) if message else "No message", 
            progress=progress, 
            payload=payload
        )
        
        event_queue.put(event, block=False)
    except Exception as e:
        # Best-effort emit: never break the pipeline due to UI queue issues
        print(f"Emit error: {e}")  # Debug output
        pass


