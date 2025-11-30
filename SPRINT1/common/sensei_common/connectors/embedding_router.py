"""
Embedding router for Sensei 2.0.

Responsible for:
- Loading embedding providers and routes from YAML.
- Resolving which provider(s) to use for a given use_case.
- Supporting primary-fallback and weighted strategies.

YAML format expected (embedding_routes.yaml):

version: "1.0"
providers:
  azure-embed:
    provider_type: azure_openai
    endpoint: "${AZURE_OPENAI_ENDPOINT}"
    api_key: "${AZURE_OPENAI_KEY}"
    model: "text-embedding-3-large"
    embedding_dim: 3072
    timeout_ms: 5000
    retries: 3
routes:
  vendor.embedding:
    strategy: primary-fallback
    providers: [azure-embed, hf-endpoint, groq-embed]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import yaml


@dataclass
class EmbeddingProvider:
    """
    Configuration for a single embedding provider.
    """

    name: str
    provider_type: str
    endpoint: str
    api_key: str
    model: str
    embedding_dim: int
    timeout_ms: int
    retries: int


@dataclass
class EmbeddingRoute:
    """
    Routing rules for a use case.
    """

    name: str
    strategy: str
    providers: List[str]
    weights: Optional[List[int]] = None


class EmbeddingRouter:
    """
    Router for embedding providers based on use-case routes.

    This class is pure config logic, no HTTP calls.
    Actual HTTP call is done in EmbeddingClient.
    """

    def __init__(
        self,
        providers: Dict[str, EmbeddingProvider],
        routes: Dict[str, EmbeddingRoute],
        default_route: EmbeddingRoute,
    ) -> None:
        self._providers = providers
        self._routes = routes
        self._default_route = default_route

    @classmethod
    def from_yaml_file(cls, path: str) -> "EmbeddingRouter":
        """
        Build an EmbeddingRouter from a YAML file.

        Parameters
        ----------
        path : str
            Path to embedding_routes.yaml.

        Returns
        -------
        EmbeddingRouter
        """
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        providers_cfg = data.get("providers", {})
        routes_cfg = data.get("routes", {})

        providers: Dict[str, EmbeddingProvider] = {}
        for name, cfg in providers_cfg.items():
            providers[name] = EmbeddingProvider(
                name=name,
                provider_type=cfg["provider_type"],
                endpoint=cfg["endpoint"],
                api_key=cfg.get("api_key", ""),
                model=cfg["model"],
                embedding_dim=int(cfg["embedding_dim"]),
                timeout_ms=int(cfg.get("timeout_ms", 5000)),
                retries=int(cfg.get("retries", 3)),
            )

        routes: Dict[str, EmbeddingRoute] = {}
        default_route: Optional[EmbeddingRoute] = None

        for route_name, rcfg in routes_cfg.items():
            route = EmbeddingRoute(
                name=route_name,
                strategy=rcfg["strategy"],
                providers=rcfg["providers"],
                weights=rcfg.get("weights"),
            )
            if route_name == "default":
                default_route = route
            else:
                routes[route_name] = route

        if default_route is None:
            raise ValueError("embedding_routes.yaml must define a 'default' route")

        return cls(providers=providers, routes=routes, default_route=default_route)

    def resolve_route(self, use_case: str) -> EmbeddingRoute:
        """
        Resolve a route for a use case, falling back to default.

        Parameters
        ----------
        use_case : str
            Use case name, e.g. "vendor.embedding".

        Returns
        -------
        EmbeddingRoute
        """
        return self._routes.get(use_case, self._default_route)

    def get_provider(self, name: str) -> EmbeddingProvider:
        """
        Get an embedding provider by name.

        Raises KeyError if unknown.
        """
        return self._providers[name]
