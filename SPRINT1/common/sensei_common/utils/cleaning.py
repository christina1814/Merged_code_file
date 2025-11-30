"""
Shared text/markdown cleaning utilities for VKIS and Authoring.

This does not try to be perfect; just removes common noise and normalizes whitespace.
"""

from __future__ import annotations

import re


_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINES_RE = re.compile(r"\n{3,}")


def normalize_whitespace(text: str) -> str:
    text = _WHITESPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINES_RE.sub("\n\n", text)
    return text.strip()


def strip_toc(text: str) -> str:
    """
    Remove simple 'Table of contents' blocks.
    Very heuristic; safe to run multiple times.
    """
    return re.sub(
        r"(Table of contents.*?)(\n#+\s|\Z)",
        r"\2",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )


def strip_navigation(text: str) -> str:
    """
    Remove obvious nav/footer strings from vendor docs.
    (You can tune this list later.)
    """
    patterns = [
        r"© [0-9]{4} Microsoft Corporation.*",
        r"All rights reserved\.",
        r"Was this page helpful\?.*",
    ]
    cleaned = text
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    return cleaned


def clean_markdown(md: str) -> str:
    """
    Apply all cleaning steps:
    - strip nav/footer
    - strip TOC
    - normalize whitespace
    """
    text = strip_navigation(md)
    text = strip_toc(text)
    text = normalize_whitespace(text)
    return text
