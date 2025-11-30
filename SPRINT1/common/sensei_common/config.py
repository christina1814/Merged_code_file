"""
Sensei 2.0 — Central Config Loader (Pydantic Settings)

This module centralizes loading ENV, YAML-based routes (LLM + Embeddings),
Kafka settings, Redis, Blob, Postgres parameters and logging config.

Teams MUST import from here instead of reloading ENV directly.

Usage:

from sensei_common.config import settings
from sensei_common.connectors import PostgresClient

db = PostgresClient(
    dsn=settings.POSTGRES_DSN,
    component=settings.COMPONENT_NAME,
)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "configs"


class Settings(BaseSettings):
    """
    Central configuration using Pydantic Settings (v2).
    Overrides order:
    1. Environment variables
    2. .env file (optional)
    3. Defaults below
    """

    # -----------------------------
    # Service Identity
    # -----------------------------
    COMPONENT_NAME: str = Field("common", description="Logical component name")

    # -----------------------------
    # Postgres
    # -----------------------------
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "sensei"
    POSTGRES_USER: str = "sensei"
    POSTGRES_PASSWORD: str = "sensei"
    POSTGRES_POOL_MIN: int = 1
    POSTGRES_POOL_MAX: int = 10

    @property
    def POSTGRES_DSN(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # -----------------------------
    # Redis
    # -----------------------------
    REDIS_URL: str = "redis://redis:6379/0"

    # -----------------------------
    # Kafka (Apache Kafka on AKS)
    # -----------------------------
    KAFKA_BOOTSTRAP: str = "kafka-0.kafka.svc:9092,kafka-1.kafka.svc:9092"
    KAFKA_GROUP_PREFIX: str = "sensei"

    # -----------------------------
    # Azure Blob Storage
    # -----------------------------
    AZURE_BLOB_ACCOUNT_URL: str = "https://senseistorage.blob.core.windows.net/"
    AZURE_BLOB_CONTAINER: str = "sensei"
    AZURE_BLOB_SAS_KEY: str = ""  # loaded via ENV

    # -----------------------------
    # Azure AI Search
    # -----------------------------
    AZURE_SEARCH_ENDPOINT: str = ""
    AZURE_SEARCH_ADMIN_KEY: str = ""
    AZURE_SEARCH_INDEX_VENDOR: str = "vendor_docs_index"
    AZURE_SEARCH_INDEX_QA: str = "vendor_qbank_index"

    # -----------------------------
    # Embedding/LLM Config Paths
    # -----------------------------
    EMBEDDING_YAML: str = str(CONFIG_DIR / "embedding_routes.yaml")
    LLM_YAML: str = str(CONFIG_DIR / "llm_routes.yaml")
    LOGGING_YAML: str = str(CONFIG_DIR / "logging.yaml")
    KAFKA_YAML: str = str(CONFIG_DIR / "kafka_config.yaml")
    PLATFORM_YAML: str = str(CONFIG_DIR / "platform.yaml")
    ONTOLOGY_YAML: str = str(CONFIG_DIR / "ontology.yaml")

    # -----------------------------
    # Telemetry
    # -----------------------------
    ELASTIC_URL: str = ""
    ELASTIC_API_KEY: str = ""
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = ""

    # -----------------------------
    # Misc Runtime Settings
    # -----------------------------
    ENV: str = Field("dev", description="dev / staging / prod")
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    # ------------------------------------------------------------------
    # YAML Loader Utilities
    # ------------------------------------------------------------------

    def load_yaml(self, path: str) -> Dict[str, Any]:
        """Load any YAML file (embedding, llm, logging)."""
        if not Path(path).exists():
            raise FileNotFoundError(f"YAML not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)


# Create global settings instance
settings = Settings()

__all__ = ["settings"]
