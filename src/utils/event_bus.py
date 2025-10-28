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


def emit(event_queue, stage: str, substage: str, message: str,
         level: str = "info", progress: Optional[float] = None,
         payload: Optional[Dict[str, Any]] = None) -> None:
    """Put a PipelineEvent into the provided queue."""
    try:
        event_queue.put(
            PipelineEvent(stage=stage, substage=substage, level=level,
                          message=message, progress=progress, payload=payload),
            block=False,
        )
    except Exception:
        # Best-effort emit: never break the pipeline due to UI queue issues
        pass


