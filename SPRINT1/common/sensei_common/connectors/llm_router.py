"""
LLM Router for Sensei 2.0.

Responsibilities:
- Load text-generation providers and routes from YAML.
- Support primary-fallback and weighted strategies.
- Call Azure OpenAI, Groq, HuggingFace, etc.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx
import yaml

from common.sensei_common.logging.logger import get_logger


@dataclass
class LLMProvider:
    """
    Configuration for an LLM generation provider.
    """

    name: str
    provider_type: str
    endpoint: str
    api_key: str
    model: str
    timeout_ms: int
    retries: int


@dataclass
class LLMRoute:
    """
    Routing rules for a generation use case.
    """

    name: str
    strategy: str
    providers: List[str]
    weights: Optional[List[int]] = None


class LLMRouter:
    """
    Router for LLM generation calls.

    This class hides provider-specific HTTP details from callers.
    """

    def __init__(
        self,
        providers: Dict[str, LLMProvider],
        routes: Dict[str, LLMRoute],
        default_route: LLMRoute,
        component: str = "common",
    ) -> None:
        self._providers = providers
        self._routes = routes
        self._default_route = default_route
        self._component = component

    @classmethod
    def from_yaml_file(cls, path: str, component: str = "common") -> "LLMRouter":
        """
        Build an LLMRouter from a YAML file.

        Parameters
        ----------
        path : str
            Path to llm_routes.yaml.
        component : str
            Component label.

        Returns
        -------
        LLMRouter
        """
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        providers_cfg = data.get("providers", {})
        routes_cfg = data.get("routes", {})

        providers: Dict[str, LLMProvider] = {}
        for name, cfg in providers_cfg.items():
            providers[name] = LLMProvider(
                name=name,
                provider_type=cfg["provider_type"],
                endpoint=cfg["endpoint"],
                api_key=cfg.get("api_key", ""),
                model=cfg["model"],
                timeout_ms=int(cfg.get("timeout_ms", 10000)),
                retries=int(cfg.get("retries", 3)),
            )

        routes: Dict[str, LLMRoute] = {}
        default_route: Optional[LLMRoute] = None

        for route_name, rcfg in routes_cfg.items():
            route = LLMRoute(
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
            raise ValueError("llm_routes.yaml must define a 'default' route")

        return cls(providers=providers, routes=routes, default_route=default_route, component=component)

    def _resolve_route(self, use_case: str) -> LLMRoute:
        return self._routes.get(use_case, self._default_route)

    async def generate(
        self,
        prompt: str,
        use_case: str,
        trace_id: Optional[str] = None,
    ) -> str:
        """
        Generate text using an LLM according to routing rules.

        Parameters
        ----------
        prompt : str
            Prompt to send to the LLM.
        use_case : str
            Logical use case (e.g. "authoring.generate").
        trace_id : Optional[str]
            Correlation ID.

        Returns
        -------
        str
            Generated text.
        """
        logger = get_logger(self._component, "llm", "LLMRouter.generate", trace_id)
        route = self._resolve_route(use_case)

        providers = [self._providers[name] for name in route.providers]

        if route.strategy == "weighted" and route.weights:
            provider = random.choices(providers, weights=route.weights, k=1)[0]
            return await self._call_provider(provider, prompt, trace_id)

        # primary-fallback
        last_error: Optional[Exception] = None
        for provider in providers:
            try:
                return await self._call_provider(provider, prompt, trace_id)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.error(
                    "LLM provider=%s failed: %s",
                    provider.name,
                    exc,
                    ka_code="KA-LLM-0007",
                )
                continue

        if last_error is not None:
            raise last_error
        raise RuntimeError("LLM routing failed without explicit exception")

    async def _call_provider(
        self,
        provider: LLMProvider,
        prompt: str,
        trace_id: Optional[str],
    ) -> str:
        """
        Call a provider over HTTP and normalize the response.
        """
        logger = get_logger(
            self._component, "llm", f"_call_{provider.provider_type}", trace_id
        )
        headers = {}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        timeout = provider.timeout_ms / 1000.0

        for attempt in range(1, provider.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    payload = self._build_payload(provider, prompt)
                    resp = await client.post(
                        provider.endpoint,
                        headers=headers,
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    text = self._extract_text(provider, data)
                    logger.info("LLM provider=%s attempt=%d succeeded", provider.name, attempt)
                    return text
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "LLM provider=%s attempt=%d failed: %s",
                    provider.name,
                    attempt,
                    exc,
                )
                if attempt == provider.retries:
                    raise

        raise RuntimeError("LLM provider retries exhausted")

    @staticmethod
    def _build_payload(provider: LLMProvider, prompt: str) -> Dict:
        """
        Build provider-specific request payload.
        """
        if provider.provider_type == "azure_openai":
            return {
                "messages": [{"role": "user", "content": prompt}],
                "model": provider.model,
            }
        if provider.provider_type == "groq":
            return {
                "messages": [{"role": "user", "content": prompt}],
                "model": provider.model,
            }
        if provider.provider_type == "huggingface_api":
            return {"inputs": prompt}
        # Default generic payload
        return {"input": prompt, "model": provider.model}

    @staticmethod
    def _extract_text(provider: LLMProvider, data: Dict) -> str:
        """
        Extract generated text from provider-specific response.
        """
        if provider.provider_type in {"azure_openai", "groq"}:
            return data["choices"][0]["message"]["content"]
        if provider.provider_type == "huggingface_api":
            # HF may return a list of generations
            if isinstance(data, list) and data:
                item = data[0]
                if isinstance(item, dict) and "generated_text" in item:
                    return item["generated_text"]
            return str(data)
        # Default fallback
        return str(data)
