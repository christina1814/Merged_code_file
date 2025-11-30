"""
Telemetry client for Sensei 2.0.

Responsibilities:
- Emit metrics to Elastic/Prometheus (via sidecar/agent)
- Emit traces/events to Langfuse
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from common.sensei_common.logging.logger import get_logger


class TelemetryClient:
    """
    Lightweight telemetry client.

    This is a thin abstraction; actual integration with Elastic,
    Prometheus, or Langfuse should be wired in according to your
    deployment (agent, SDK, etc.).
    """

    def __init__(
        self,
        component: str = "common",
    ) -> None:
        self._component = component

    def emit_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Emit a numeric metric.

        In production, send this to your metrics backend.
        """
        logger = get_logger(self._component, "metrics", name, trace_id)
        logger.info("metric=%s value=%s labels=%s", name, value, labels or {})

    def log_span(
        self,
        span_name: str,
        duration_ms: float,
        attributes: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Log a span for tracing.
        """
        logger = get_logger(self._component, "trace", span_name, trace_id)
        logger.info(
            "span=%s duration_ms=%.2f attrs=%s",
            span_name,
            duration_ms,
            attributes or {},
        )

    def log_llm_event(
        self,
        provider: str,
        tokens: int,
        latency_ms: float,
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Log an LLM usage event. Can be forwarded to Langfuse or similar.
        """
        logger = get_logger(self._component, "llm", "usage", trace_id)
        logger.info(
            "provider=%s tokens=%d latency_ms=%.2f",
            provider,
            tokens,
            latency_ms,
        )
