"""
Event bus utilities for dashboard → pipeline communication.

Provides a simple dataclass for pipeline events and helper functions to
emit events into a thread-safe Queue. Designed to be lightweight and to
avoid introducing heavy dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PipelineEvent:
    stage: str
    substage: str
    level: str
    message: str
    progress: Optional[float] = None
    payload: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Ensure all fields are properly initialized."""
        if self.stage is None:
            self.stage = "unknown"
        if self.substage is None:
            self.substage = "unknown"
        if self.level is None:
            self.level = "info"
        if self.message is None:
            self.message = "No message"


def emit(event_queue, stage: str, substage: str, message: str,
         level: str = "info", progress: Optional[float] = None,
         payload: Optional[Dict[str, Any]] = None) -> None:
    """Put a PipelineEvent into the provided queue."""
    try:
        # Safety checks for parameters
        if event_queue is None:
            return
        if stage is None:
            stage = "unknown"
        if substage is None:
            substage = "unknown"
        if message is None:
            message = "No message"
        if level is None:
            level = "info"
            
        event_queue.put(
            PipelineEvent(stage=stage, substage=substage, level=level,
                          message=message, progress=progress, payload=payload),
            block=False,
        )
    except Exception:
        # Best-effort emit: never break the pipeline due to UI queue issues
        pass


