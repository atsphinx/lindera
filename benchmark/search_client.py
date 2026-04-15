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


def _as_set(entry: int | list[int]) -> set[int]:
    """Normalize a searchindex entry (int or list) to a set of doc indices."""
    if isinstance(entry, int):
        return {entry}
    return set(entry)


def search(index: dict, query_tokens: list[str]) -> list[str]:
    """Return document names matching all query tokens (AND search).

    Replicates the core logic of Sphinx's searchtools.js:
    - Sphinx's word_filter (tokens with length <= 1 are discarded)
    - Each token is looked up in both ``terms`` (body) and ``titleterms``
      (section headings); the union of both is used per token
    - An AND intersection is applied across all tokens
    """
    # Mirror sphinx.search.SearchLanguage.word_filter: len > 1 required.
    filtered = [t for t in query_tokens if len(t) > 1]
    if not filtered:
        return []

    terms = index.get("terms", {})
    titleterms = index.get("titleterms", {})
    docnames = index.get("docnames", [])

    result_sets: list[set[int]] = []
    for token in filtered:
        # Union of body-text and title matches (mirrors searchtools.js)
        docs = _as_set(terms.get(token, [])) | _as_set(titleterms.get(token, []))
        result_sets.append(docs)

    if not result_sets:
        return []

    doc_indices = result_sets[0]
    for s in result_sets[1:]:
        doc_indices = doc_indices & s

    return [docnames[i] for i in sorted(doc_indices) if i < len(docnames)]
