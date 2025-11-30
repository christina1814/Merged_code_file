"""
Ontology helpers for Sensei 2.0.

Shared by:
- VKIS: classify vendor pages/chunks
- Authoring: classify KB articles

Uses:
- YAML rules first (cheap, deterministic)
- Optional LLM fallback (Azure/Groq/HF/Ollama via LLMRouter)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sensei_common.config import settings
from sensei_common.connectors.llm_router import LLMRouter
from sensei_common.utils.exceptions import LLMError


@dataclass
class OntologyLabel:
    doc_kind: str   # troubleshooting, how-to, reference, concept, release-notes, general
    area: str       # network, compute, storage, security, observability, general
    score: float    # 0.0–1.0 overall confidence


def _load_ontology_config() -> Dict:
    """
    Load ontology.yaml via central config.

    If file missing, returns a minimal default config.
    """
    try:
        path = getattr(settings, "ONTOLOGY_YAML", None)
        if not path:
            raise FileNotFoundError("ONTOLOGY_YAML not configured")
        return settings.load_yaml(path)
    except FileNotFoundError:
        return {
            "doc_kinds": {
                "general": {"keywords": []},
            },
            "areas": {
                "general": {"keywords": []},
            },
            "llm_fallback": {
                "enabled": False,
                "use_route": "default",
                "min_rule_score": 0.6,
                "labels": {
                    "doc_kind": ["general"],
                    "area": ["general"],
                },
            },
        }


_CONFIG = _load_ontology_config()
_DOC_KINDS: Dict[str, List[str]] = {
    name: cfg.get("keywords", []) for name, cfg in _CONFIG.get("doc_kinds", {}).items()
}
_AREAS: Dict[str, List[str]] = {
    name: cfg.get("keywords", []) for name, cfg in _CONFIG.get("areas", {}).items()
}
_LLM_CFG: Dict = _CONFIG.get("llm_fallback", {}) or {}

_LLM_ROUTER: Optional[LLMRouter] = None


def _get_llm_router() -> LLMRouter:
    global _LLM_ROUTER
    if _LLM_ROUTER is None:
        _LLM_ROUTER = LLMRouter.from_yaml_file(settings.LLM_YAML, component="ontology")
    return _LLM_ROUTER


def _score_category(text: str, categories: Dict[str, List[str]]) -> Tuple[str, float]:
    lower = text.lower()
    best_cat = "general"
    best_score = 0.0

    for name, keywords in categories.items():
        if not keywords:
            continue
        matches = sum(1 for kw in keywords if kw.lower() in lower)
        if matches == 0:
            continue
        score = matches / float(len(keywords))
        if score > best_score:
            best_score = score
            best_cat = name

    if best_score == 0.0 and "general" in categories:
        best_cat = "general"

    return best_cat, best_score


def _rule_based_classify(text: str) -> OntologyLabel:
    doc_kind, kind_score = _score_category(text, _DOC_KINDS)
    area, area_score = _score_category(text, _AREAS)
    score = (kind_score + area_score) / 2.0 if (kind_score or area_score) else 0.0
    return OntologyLabel(doc_kind=doc_kind, area=area, score=score)


async def _llm_enrich_ontology(
    text: str,
    base: OntologyLabel,
    trace_id: Optional[str] = None,
) -> OntologyLabel:
    enabled = _LLM_CFG.get("enabled", False)
    if not enabled:
        return base

    use_route = _LLM_CFG.get("use_route", "ontology.classify")
    labels_cfg = _LLM_CFG.get("labels", {})
    doc_kind_labels = labels_cfg.get("doc_kind", [base.doc_kind])
    area_labels = labels_cfg.get("area", [base.area])

    router = _get_llm_router()

    system_prompt = (
        "You are an ontology classifier for IT documentation. "
        "Respond with a single JSON object only."
    )

    user_prompt = f"""
Available doc_kind labels: {', '.join(doc_kind_labels)}
Available area labels: {', '.join(area_labels)}

Classify the following text into one doc_kind and one area.
Return JSON with exactly: doc_kind, area, score (0.0–1.0).

Text:
<<<
{text[:4000]}
>>>

Current rule-based guess:
doc_kind = {base.doc_kind}
area = {base.area}
score = {base.score:.2f}
"""

    prompt = f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{user_prompt}"

    try:
        raw = await router.generate(prompt=prompt, use_case=use_route, trace_id=trace_id)
        parsed = json.loads(raw)
        doc_kind = str(parsed.get("doc_kind", base.doc_kind))
        area = str(parsed.get("area", base.area))
        try:
            score = float(parsed.get("score", base.score))
        except (TypeError, ValueError):
            score = base.score

        return OntologyLabel(doc_kind=doc_kind, area=area, score=score)
    except Exception as e:  # noqa: BLE001
        raise LLMError("KA-LLM-0007", f"Ontology LLM fallback failed: {e}")


async def classify_ontology(
    text: str,
    trace_id: Optional[str] = None,
) -> OntologyLabel:
    base = _rule_based_classify(text)
    min_rule_score = float(_LLM_CFG.get("min_rule_score", 0.6))

    if not _LLM_CFG.get("enabled", False):
        return base

    if base.score >= min_rule_score:
        return base

    try:
        enriched = await _llm_enrich_ontology(text, base, trace_id=trace_id)
        return enriched
    except LLMError:
        return base
