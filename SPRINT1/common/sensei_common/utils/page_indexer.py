"""
Page index builder – converts Markdown headings into a logical index tree.

Used by:
- VKIS (vendor docs)
- Authoring (L3 ontology and chunk metadata)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class HeadingNode:
    level: int
    title: str
    line_no: int
    index_path: str  # e.g., "1", "1.2", "1.2.3"
    anchor: str      # simplified slug (for future use)


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9\-]+", "-", title.lower()).strip("-")


def build_page_index(md: str) -> List[HeadingNode]:
    """
    Parse headings and build a linear list with level + index_path.

    Example:
      # Install Agent         -> 1
      ## Linux                -> 1.1
      ## Windows              -> 1.2
      ### Service Account     -> 1.2.1
    """
    lines = md.splitlines()
    counters = [0] * 6
    nodes: List[HeadingNode] = []

    for i, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line.strip())
        if not m:
            continue

        hashes, title = m.groups()
        level = len(hashes)
        if level < 1 or level > 6:
            continue

        counters[level - 1] += 1
        # reset deeper levels
        for j in range(level, 6):
            counters[j] = 0

        nums = [str(counters[k]) for k in range(level) if counters[k] > 0]
        index_path = ".".join(nums)
        anchor = _slugify(title)

        nodes.append(
            HeadingNode(
                level=level,
                title=title.strip(),
                line_no=i,
                index_path=index_path,
                anchor=anchor,
            )
        )

    return nodes
