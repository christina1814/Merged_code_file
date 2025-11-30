"""
Shared exception hierarchy for Sensei 2.0.

All services should raise SenseiError (or subclasses) with a KA code.
"""

from __future__ import annotations

from typing import Optional

from common.sensei_common.utils.error_codes import get_error_info, ErrorInfo


class SenseiError(Exception):
    """Base exception for all platform errors."""

    def __init__(
        self,
        code: str,
        message: Optional[str] = None,
        *,
        http_status: Optional[int] = None,
        retriable: Optional[bool] = None,
    ) -> None:
        self.info: ErrorInfo = get_error_info(code)
        self.code: str = self.info.code
        self.http_status: int = http_status or self.info.http_status
        self.retriable: bool = retriable if retriable is not None else self.info.retriable
        self.detail: str = message or self.info.description
        super().__init__(f"{self.code}: {self.detail}")


class APIError(SenseiError):
    """API layer errors (validation, auth, mapping)."""


class DBError(SenseiError):
    """Database-related errors."""


class KafkaError(SenseiError):
    """Kafka / event bus errors."""


class LLMError(SenseiError):
    """LLM / embedding provider errors."""


class IndexingError(SenseiError):
    """Indexing / Azure AI Search / hybrid search errors."""


class SecurityError(SenseiError):
    """Security / auth / scan errors."""


class PipelineError(SenseiError):
    """ETL / enrichment / Flyte pipeline errors."""


class ValidationError(SenseiError):
    """Payload or taxonomy validation errors."""
