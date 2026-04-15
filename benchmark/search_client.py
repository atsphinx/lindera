"""Utilities to parse searchindex.js and execute queries against it."""

from __future__ import annotations

import json
import re
from pathlib import Path


def load_index(build_dir: Path) -> dict:
    """Parse searchindex.js from a Sphinx HTML build directory."""
    raw = (build_dir / "searchindex.js").read_text(encoding="utf-8")
    # File format: Search.setIndex({...})
    match = re.search(r"Search\.setIndex\((.+)\)", raw, re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse searchindex.js in {build_dir}")
    return json.loads(match.group(1))


def search(index: dict, query_tokens: list[str]) -> list[str]:
    """Return document names matching all query tokens (AND search).

    Replicates the core logic of Sphinx's searchtools.js.
    """
    if not query_tokens:
        return []

    terms = index.get("terms", {})
    docnames = index.get("docnames", [])

    result_sets: list[set[int]] = []
    for token in query_tokens:
        entry = terms.get(token, [])
        # Sphinx stores a bare int when there is only one matching document.
        if isinstance(entry, int):
            entry = [entry]
        result_sets.append(set(entry))

    if not result_sets:
        return []

    doc_indices = result_sets[0]
    for s in result_sets[1:]:
        doc_indices = doc_indices & s

    return [docnames[i] for i in sorted(doc_indices) if i < len(docnames)]
