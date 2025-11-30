"""
Embedding client for Sensei 2.0.

Responsibilities:
- Use EmbeddingRouter to resolve providers for a given use case.
- Use Redis for caching (fingerprint-based).
- Call external embedding APIs for:
  - Azure OpenAI
  - HuggingFace (hosted / endpoint)
  - Groq
  - Ollama
- Validate embedding dimension.
"""

from __future__ import annotations

import hashlib
import json
from typing import List, Optional

import httpx

from common.sensei_common.connectors.embedding_router import EmbeddingRouter, EmbeddingProvider
from common.sensei_common.connectors.redis_client import RedisClient
from common.sensei_common.logging.logger import get_logger


class EmbeddingClient:
    """
    High-level embedding client that uses router + Redis cache.

    This client is used by VKIS, Authoring Studio and shared workers.
    """

    def __init__(
        self,
        router: EmbeddingRouter,
        redis_client: RedisClient,
        component: str = "common",
        cache_ttl_seconds: int = 7 * 24 * 3600,
    ) -> None:
        """
        Initialize the embedding client.

        Parameters
        ----------
        router : EmbeddingRouter
            Routing configuration for embedding providers.
        redis_client : RedisClient
            Redis client used for caching embeddings.
        component : str
            Component label (e.g. "vendor", "authoring", "common").
        cache_ttl_seconds : int
            Cache TTL in seconds.
        """
        self._router = router
        self._redis = redis_client
        self._component = component
        self._ttl = cache_ttl_seconds

    @staticmethod
    def _fingerprint(text: str, model: str) -> str:
        """
        Build a stable fingerprint for a text + model pair.
        """
        normalized = " ".join(text.split())
        raw = f"{model}::{normalized}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    async def embed(
        self,
        texts: List[str],
        use_case: str,
        trace_id: Optional[str] = None,
    ) -> List[List[float]]:
        """
        Embed a list of texts for a given use case.

        Parameters
        ----------
        texts : List[str]
            Texts to embed.
        use_case : str
            Use case name, e.g. "vendor.embedding".
        trace_id : Optional[str]
            Correlation ID.

        Returns
        -------
        List[List[float]]
            Embedding vectors.
        """
        logger = get_logger(self._component, "embed", "EmbeddingClient", trace_id)
        route = self._router.resolve_route(use_case)
        providers = [self._router.get_provider(name) for name in route.providers]

        results: List[List[float]] = []
        for text in texts:
            vector = await self._embed_single(text, providers, route.strategy, trace_id)
            results.append(vector)

        logger.info("Embedded %d texts with use_case=%s", len(texts), use_case)
        return results

    async def _embed_single(
        self,
        text: str,
        providers: List[EmbeddingProvider],
        strategy: str,
        trace_id: Optional[str],
    ) -> List[float]:
        logger = get_logger(self._component, "embed", "_embed_single", trace_id)

        # Try cache first based on first provider model
        primary = providers[0]
        cache_key = f"emb:{self._fingerprint(text, primary.model)}"
        cached = await self._redis.get(cache_key, trace_id=trace_id)
        if cached:
            vector = json.loads(cached)
            if isinstance(vector, list):
                return vector

        # No cache → run providers
        last_error: Optional[Exception] = None
        for provider in providers:
            try:
                vector = await self._call_provider(provider, text, trace_id)
                if len(vector) != provider.embedding_dim:
                    logger.error(
                        "Embedding dimension mismatch for provider=%s, "
                        "expected=%d got=%d",
                        provider.name,
                        provider.embedding_dim,
                        len(vector),
                        ka_code="KA-EMB-0003",
                    )
                    continue

                # Cache using primary model fingerprint to increase reuse
                await self._redis.set(
                    cache_key,
                    json.dumps(vector),
                    ttl=self._ttl,
                    trace_id=trace_id,
                )
                return vector
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.error(
                    "Embedding call failed for provider=%s: %s",
                    provider.name,
                    exc,
                    ka_code="KA-EMB-0007",
                )
                if strategy == "primary-fallback":
                    # move to next provider
                    continue

        if last_error is not None:
            raise last_error
        raise RuntimeError("Embedding pipeline failed without explicit exception")

    async def _call_provider(
        self,
        provider: EmbeddingProvider,
        text: str,
        trace_id: Optional[str],
    ) -> List[float]:
        """
        Call a single embedding provider over HTTP.

        NOTE: This is a simplified abstraction. Adjust payload/response mapping
        based on your actual provider contracts.
        """
        logger = get_logger(
            self._component, "embed", f"_call_{provider.provider_type}", trace_id
        )

        headers = {}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        timeout = provider.timeout_ms / 1000.0

        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider.provider_type == "azure_openai":
                payload = {"input": text, "model": provider.model}
            elif provider.provider_type in {"huggingface_api", "huggingface_endpoint"}:
                payload = {"inputs": text}
            elif provider.provider_type in {"groq", "ollama"}:
                payload = {"input": text, "model": provider.model}
            else:
                raise ValueError(f"Unknown provider_type={provider.provider_type}")

            resp = await client.post(provider.endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        # Normalize response shapes into a flat vector list[float].
        if provider.provider_type == "azure_openai":
            vector = data["data"][0]["embedding"]
        elif provider.provider_type in {"huggingface_api", "huggingface_endpoint"}:
            # HF can return list[list[float]] or list[float]; flatten first row
            if isinstance(data, list) and data and isinstance(data[0], list):
                vector = data[0]
            else:
                vector = data
        elif provider.provider_type in {"groq", "ollama"}:
            vector = data["data"][0]["embedding"]
        else:
            vector = data

        logger.info(
            "Embedding provider=%s succeeded, dim=%d",
            provider.name,
            len(vector),  # type: ignore[arg-type]
        )
        return vector  # type: ignore[return-value]
