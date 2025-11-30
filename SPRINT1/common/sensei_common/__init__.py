"""
Re-export core connector classes for easier imports.

Usage:
    from sensei_common import PostgresClient, KafkaClient
"""

from .connectors.postgres_client import PostgresClient
from .connectors.redis_client import RedisClient
from .connectors.blob_client import BlobClient
from .connectors.kafka_client import KafkaClient
from .connectors.embedding_router import EmbeddingRouter
from .connectors.embedding_client import EmbeddingClient
from .connectors.llm_router import LLMRouter
from .connectors.telemetry_client import TelemetryClient

__all__ = [
    "PostgresClient",
    "RedisClient",
    "BlobClient",
    "KafkaClient",
    "EmbeddingRouter",
    "EmbeddingClient",
    "LLMRouter",
    "TelemetryClient",
]
