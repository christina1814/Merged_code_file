"""
TraceContext helpers for Sensei 2.0.

Used by:
- Kafka headers
- HTTP logs
- Telemetry events

All services should propagate trace_id/span_id from request → DB → Kafka → Flyte → Elastic.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, Optional


TRACE_HEADER_PREFIX = "x-sensei-"


@dataclass
class TraceContext:
    trace_id: str
    span_id: str
    component: str
    stage: str
    feature: str
    parent_span_id: Optional[str] = None

    def to_kafka_headers(self) -> Dict[str, bytes]:
        return {
            f"{TRACE_HEADER_PREFIX}trace-id": self.trace_id.encode("utf-8"),
            f"{TRACE_HEADER_PREFIX}span-id": self.span_id.encode("utf-8"),
            f"{TRACE_HEADER_PREFIX}parent-span-id": (
                self.parent_span_id.encode("utf-8") if self.parent_span_id else b""
            ),
            f"{TRACE_HEADER_PREFIX}component": self.component.encode("utf-8"),
            f"{TRACE_HEADER_PREFIX}stage": self.stage.encode("utf-8"),
            f"{TRACE_HEADER_PREFIX}feature": self.feature.encode("utf-8"),
        }

    @classmethod
    def from_kafka_headers(cls, headers: Dict[str, bytes]) -> "TraceContext":
        def _get(key: str) -> Optional[str]:
            raw = headers.get(f"{TRACE_HEADER_PREFIX}{key}")
            if raw is None:
                return None
            if isinstance(raw, bytes):
                return raw.decode("utf-8")
            return str(raw)

        return cls(
            trace_id=_get("trace-id") or new_trace_id(),
            span_id=_get("span-id") or new_span_id(),
            parent_span_id=_get("parent-span-id") or None,
            component=_get("component") or "unknown",
            stage=_get("stage") or "unknown",
            feature=_get("feature") or "unknown",
        )

    def as_dict(self) -> Dict[str, str]:
        return {k: str(v) for k, v in asdict(self).items() if v is not None}


def new_trace_id() -> str:
    return str(uuid.uuid4())


def new_span_id() -> str:
    return f"{int(time.time() * 1000):x}-{uuid.uuid4().hex[:8]}"


def ensure_trace(
    component: str,
    stage: str,
    feature: str,
    parent: Optional[TraceContext] = None,
) -> TraceContext:
    if parent:
        trace_id = parent.trace_id
        parent_span_id = parent.span_id
    else:
        trace_id = new_trace_id()
        parent_span_id = None

    return TraceContext(
        trace_id=trace_id,
        span_id=new_span_id(),
        parent_span_id=parent_span_id,
        component=component,
        stage=stage,
        feature=feature,
    )

