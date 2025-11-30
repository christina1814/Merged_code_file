"""
Timing utilities for profiling and metrics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Timer:
    start_ms: float
    end_ms: float = 0.0

    def stop(self) -> None:
        self.end_ms = time.time() * 1000.0

    @property
    def elapsed_ms(self) -> float:
        end = self.end_ms or (time.time() * 1000.0)
        return end - self.start_ms


def start_timer() -> Timer:
    """Return a started Timer instance."""
    return Timer(start_ms=time.time() * 1000.0)
