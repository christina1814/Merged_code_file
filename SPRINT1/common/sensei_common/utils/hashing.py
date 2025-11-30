"""
Hashing and fingerprint helpers shared by VKIS and Authoring.

Used for:
- Page deduplication
- Chunk deduplication
- Versioning comparison
"""

from __future__ import annotations

import hashlib
from typing import Optional


def sha256_hex(value: str) -> str:
    """Return SHA256 hex digest for a string."""
    if value is None:
        value = ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def doc_fingerprint(source: str, url_or_path: str, content: str) -> str:
    """
    Build a stable fingerprint for a full document.

    VKIS: use (source, url, cleaned_markdown)
    Authoring: use (tenant, doc_id, normalized_body)
    """
    base = f"{source}|{url_or_path}|{content}"
    return sha256_hex(base)


def chunk_fingerprint(
    doc_id: str,
    index_path: str,
    content: str,
    extra: Optional[str] = None,
) -> str:
    """
    Fingerprint for a chunk.

    Combine:
    - doc_id (or URL)
    - logical index path (section > subsection > topic)
    - cleaned content
    - optional extra (e.g., version or ontology label)
    """
    base = f"{doc_id}|{index_path}|{content}"
    if extra:
        base = f"{base}|{extra}"
    return sha256_hex(base)
