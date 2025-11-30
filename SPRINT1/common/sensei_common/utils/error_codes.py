"""
KA error code registry for Sensei 2.0.

Each code has:
- description
- default http_status
- retriable flag
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ErrorInfo:
    code: str
    description: str
    http_status: int = 500
    retriable: bool = False


# Core registry
_KA_REGISTRY: Dict[str, ErrorInfo] = {
    # API / Validation
    "KA-API-0001": ErrorInfo("KA-API-0001", "Generic API error", 500, False),
    "KA-API-0002": ErrorInfo("KA-API-0002", "Invalid request payload", 400, False),

    # Database
    "KA-DB-0003": ErrorInfo("KA-DB-0003", "Database write/read failure", 500, True),

    # Kafka / Bus
    "KA-BUS-0010": ErrorInfo("KA-BUS-0010", "Kafka publish/consume failure", 502, True),

    # Security
    "KA-SEC-0051": ErrorInfo("KA-SEC-0051", "Unauthorized or forbidden", 403, False),
    "KA-SEC-0100": ErrorInfo("KA-SEC-0100", "Security scan failure", 500, True),

    # LLM / ML
    "KA-LLM-0007": ErrorInfo("KA-LLM-0007", "LLM timeout or provider failure", 504, True),
    "KA-ML-0001": ErrorInfo("KA-ML-0001", "Model load/inference error", 500, True),

    # Pipeline / Enrichment
    "KA-PIPE-0001": ErrorInfo("KA-PIPE-0001", "Metadata extraction failed", 500, True),
    "KA-PIPE-0002": ErrorInfo("KA-PIPE-0002", "Empty enrichment output", 500, False),
    "KA-PIPE-0003": ErrorInfo("KA-PIPE-0003", "Chunking failure", 500, True),

    # Indexing / Search
    "KA-IDX-0040": ErrorInfo("KA-IDX-0040", "Index or vector dimension mismatch", 500, True),
    "KA-SRCH-0001": ErrorInfo("KA-SRCH-0001", "Search query failure", 500, True),

    # QA / QAGen
    "KA-QA-0001": ErrorInfo("KA-QA-0001", "Invalid or empty QA generation output", 500, True),

    # Templates / Config
    "KA-TPL-0001": ErrorInfo("KA-TPL-0001", "Invalid template schema", 400, False),
    "KA-PRM-0001": ErrorInfo("KA-PRM-0001", "Invalid prompt JSON", 400, False),
    "KA-CFG-0001": ErrorInfo("KA-CFG-0001", "Duplicate or invalid configuration", 400, False),
    "KA-I18N-0001": ErrorInfo("KA-I18N-0001", "Missing or invalid locale", 400, False),

    # Audit / Reporting
    "KA-AUD-0001": ErrorInfo("KA-AUD-0001", "Lineage gap or missing audit link", 500, False),
    "KA-AUD-0002": ErrorInfo("KA-AUD-0002", "Reporting aggregation failure", 500, True),

    # Registry / Routes
    "KA-REG-0001": ErrorInfo("KA-REG-0001", "Invalid provider route configuration", 500, False),

    # Publishing
    "KA-PUB-0001": ErrorInfo("KA-PUB-0001", "Invalid state for publish / version control", 400, False),
}


def get_error_info(code: str) -> ErrorInfo:
    """Return ErrorInfo for a given KA code, or a generic one if not registered."""
    return _KA_REGISTRY.get(
        code,
        ErrorInfo(code=code, description="Unknown Sensei error code", http_status=500, retriable=False),
    )
