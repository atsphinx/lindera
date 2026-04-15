"""Benchmark runner: compare search quality across Sphinx Japanese splitters.

Usage:
    uv run python -m benchmark.run
"""

from __future__ import annotations

import importlib
import io
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import sphinx.application

from benchmark.queries import QUERIES
from benchmark.search_client import load_index, search

CORPUS_DIR = Path(__file__).parent / "corpus"

# ---------------------------------------------------------------------------
# Splitter registry
# ---------------------------------------------------------------------------
# Each entry: (display_name, html_search_options type value, full class path)
# - type_value=None means do not set 'type' in html_search_options (Sphinx default)
# - type_value=<dotted path> is passed as html_search_options['type']
# Add LindiraSplitter here once it is implemented.
SPLITTER_REGISTRY: list[tuple[str, str | None, str]] = [
    (
        "DefaultSplitter",
        None,  # Sphinx 8.x: omit 'type' to use DefaultSplitter
        "sphinx.search.ja.DefaultSplitter",
    ),
    (
        "JanomeSplitter",
        "sphinx.search.ja.JanomeSplitter",
        "sphinx.search.ja.JanomeSplitter",
    ),
    (
        "MecabSplitter",
        "sphinx.search.ja.MecabSplitter",
        "sphinx.search.ja.MecabSplitter",
    ),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class QueryResult:
    """Result of a single query against a built search index."""

    query_id: str
    query: str
    description: str
    tokens: list[str]
    results: list[str]
    expected: list[str]
    not_expected: list[str]

    @property
    def tp(self) -> int:
        """True positives: expected documents that were found."""
        return sum(1 for d in self.expected if d in self.results)

    @property
    def fn(self) -> int:
        """False negatives: expected documents that were not found."""
        return sum(1 for d in self.expected if d not in self.results)

    @property
    def fp(self) -> int:
        """False positives: unexpected documents that appeared in results."""
        return sum(1 for d in self.not_expected if d in self.results)


@dataclass
class SplitterResult:
    """Aggregated benchmark result for one splitter."""

    name: str
    available: bool
    unavailable_reason: str = ""
    build_time: float = 0.0
    index_size: int = 0
    query_results: list[QueryResult] = field(default_factory=list)

    @property
    def precision(self) -> float:
        """Macro-averaged precision across all queries."""
        tp = sum(r.tp for r in self.query_results)
        fp = sum(r.fp for r in self.query_results)
        return tp / (tp + fp) if (tp + fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        """Macro-averaged recall across all queries."""
        tp = sum(r.tp for r in self.query_results)
        fn = sum(r.fn for r in self.query_results)
        return tp / (tp + fn) if (tp + fn) > 0 else 0.0

    @property
    def f1(self) -> float:
        """F1 score computed from aggregated precision and recall."""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


# ---------------------------------------------------------------------------
# Build helper
# ---------------------------------------------------------------------------
def build_sphinx(splitter_type_value: str | None, output_dir: Path) -> float:
    """Build Sphinx HTML with the given splitter type, return elapsed seconds."""
    sink = io.StringIO()
    if splitter_type_value is None:
        search_options: dict = {}
    else:
        search_options = {"type": splitter_type_value}
    start = time.perf_counter()
    app = sphinx.application.Sphinx(
        srcdir=str(CORPUS_DIR),
        confdir=str(CORPUS_DIR),
        outdir=str(output_dir),
        doctreedir=str(output_dir / ".doctrees"),
        buildername="html",
        confoverrides={"html_search_options": search_options},
        status=sink,
        warning=sink,
    )
    app.build()
    return time.perf_counter() - start


# ---------------------------------------------------------------------------
# Splitter instantiation helper
# ---------------------------------------------------------------------------
def load_splitter(class_path: str):
    """Import and instantiate a splitter class by its dotted path."""
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls({})


# ---------------------------------------------------------------------------
# Main benchmark logic
# ---------------------------------------------------------------------------
def run_benchmark() -> list[SplitterResult]:
    """Build Sphinx for each splitter, run all queries, and return results."""
    results: list[SplitterResult] = []

    for display_name, type_value, class_path in SPLITTER_REGISTRY:
        print(f"  [{display_name}] checking availability ...", flush=True)

        # Check splitter availability
        try:
            splitter = load_splitter(class_path)
        except Exception as exc:
            results.append(
                SplitterResult(
                    name=display_name,
                    available=False,
                    unavailable_reason=str(exc),
                )
            )
            print(f"    -> skipped: {exc}")
            continue

        result = SplitterResult(name=display_name, available=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "build"
            output_dir.mkdir()

            # Build
            print("    building index ...", flush=True)
            try:
                result.build_time = build_sphinx(type_value, output_dir)
            except Exception as exc:
                result.available = False
                result.unavailable_reason = f"build failed: {exc}"
                results.append(result)
                print(f"    -> build failed: {exc}")
                continue

            result.index_size = (output_dir / "searchindex.js").stat().st_size
            index = load_index(output_dir)

            # Run queries
            for q in QUERIES:
                tokens = splitter.split(q["query"])
                found = search(index, tokens)
                result.query_results.append(
                    QueryResult(
                        query_id=q["id"],
                        query=q["query"],
                        description=q["description"],
                        tokens=tokens,
                        results=found,
                        expected=q["expected"],
                        not_expected=q["not_expected"],
                    )
                )

        results.append(result)
        t = result.build_time
        sz = result.index_size
        print(f"    -> done (build: {t:.2f}s, index: {sz:,} bytes)")

    return results


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------
def print_summary(results: list[SplitterResult]) -> None:
    """Print a one-line-per-splitter summary table."""
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    cols = f"{'Splitter':<22} {'Build(s)':>8} {'Index(B)':>10}"
    cols += f" {'Precision':>10} {'Recall':>8} {'F1':>6}"
    header = cols
    print(header)
    print("-" * 70)
    for r in results:
        if not r.available:
            print(f"{r.name:<22}  {'N/A (unavailable)'}")
            continue
        print(
            f"{r.name:<22} {r.build_time:>8.2f} {r.index_size:>10,}"
            f" {r.precision:>9.1%} {r.recall:>7.1%} {r.f1:>5.1%}"
        )


def print_per_query(results: list[SplitterResult]) -> None:
    """Print per-query token and hit breakdown for each available splitter."""
    print("\n" + "=" * 70)
    print("PER-QUERY BREAKDOWN")
    print("=" * 70)

    available = [r for r in results if r.available and r.query_results]
    if not available:
        print("No results available.")
        return

    # Collect all query IDs in order
    query_ids = [qr.query_id for qr in available[0].query_results]

    for qid in query_ids:
        sample = next(qr for qr in available[0].query_results if qr.query_id == qid)
        print(f"\n{qid}: {sample.query!r}  ({sample.description})")
        print(f"  expected: {sample.expected}")
        for r in available:
            qr = next(x for x in r.query_results if x.query_id == qid)
            status = "OK" if qr.tp == len(qr.expected) and qr.fp == 0 else "NG"
            print(f"  [{status}] {r.name:<22}  tokens={qr.tokens}  found={qr.results}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Entry point: run the full benchmark and print results."""
    print("=" * 70)
    print("Sphinx Japanese Search Splitter Benchmark")
    print("=" * 70)
    print()

    results = run_benchmark()

    print_summary(results)
    print_per_query(results)

    unavailable = [r for r in results if not r.available]
    if unavailable:
        print("\n--- Unavailable splitters ---")
        for r in unavailable:
            print(f"  {r.name}: {r.unavailable_reason}")


if __name__ == "__main__":
    main()
