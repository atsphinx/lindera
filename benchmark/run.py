"""Benchmark runner: compare search quality across Sphinx Japanese splitters.

Usage:
    uv run python -m benchmark.run
    uv run python -m benchmark.run --exclude MecabSplitter
    uv run python -m benchmark.run --exclude MecabSplitter JanomeSplitter
"""

from __future__ import annotations

import argparse
import importlib
import io
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import sphinx.application

from benchmark.queries import QUERIES
from benchmark.search_client import load_index, search

CORPUS_DIR = Path(__file__).parent / "corpus"

# Candidate paths for mecabrc across distributions.
# Ubuntu/Debian: /etc/mecabrc
# Arch Linux:    /etc/mecabrc
# macOS Homebrew (Intel): /usr/local/etc/mecabrc
# macOS Homebrew (Apple Silicon): /opt/homebrew/etc/mecabrc
_MECABRC_CANDIDATES = [
    Path("/etc/mecabrc"),
    Path("/usr/local/etc/mecabrc"),
    Path("/opt/homebrew/etc/mecabrc"),
]


def _ensure_mecabrc() -> None:
    """Set MECABRC env var if not set and a known candidate path exists."""
    if os.environ.get("MECABRC"):
        return
    for candidate in _MECABRC_CANDIDATES:
        if candidate.exists():
            os.environ["MECABRC"] = str(candidate)
            return


_ensure_mecabrc()

# ---------------------------------------------------------------------------
# Splitter registry
# ---------------------------------------------------------------------------
# Each entry: (display_name, type_value, class_path, extra_options)
# where type_value goes into html_search_options['type']
# - type_value=None means do not set 'type' in html_search_options (Sphinx default)
# - type_value=<dotted path> is passed as html_search_options['type']
# - extra_options is merged into html_search_options and passed to the splitter instance
_LINDERA_CLASS = "atsphinx.lindera.splitter.LinderaSplitter"
SPLITTER_REGISTRY: list[tuple[str, str | None, str, dict[str, str]]] = [
    (
        "DefaultSplitter",
        None,  # Sphinx 8.x: omit 'type' to use DefaultSplitter
        "sphinx.search.ja.DefaultSplitter",
        {},
    ),
    (
        "JanomeSplitter",
        "sphinx.search.ja.JanomeSplitter",
        "sphinx.search.ja.JanomeSplitter",
        {},
    ),
    (
        "MecabSplitter",
        "sphinx.search.ja.MecabSplitter",
        "sphinx.search.ja.MecabSplitter",
        {},
    ),
    (
        "Lindera/IPAdic",
        _LINDERA_CLASS,
        _LINDERA_CLASS,
        {"dict_type": "ipadic", "mode": "normal"},
    ),
    (
        "Lindera/IPAdic/decompose",
        _LINDERA_CLASS,
        _LINDERA_CLASS,
        {"dict_type": "ipadic", "mode": "decompose"},
    ),
    (
        "Lindera/neologd",
        _LINDERA_CLASS,
        _LINDERA_CLASS,
        {"dict_type": "ipadic-neologd", "mode": "normal"},
    ),
    (
        "Lindera/neologd/decompose",
        _LINDERA_CLASS,
        _LINDERA_CLASS,
        {"dict_type": "ipadic-neologd", "mode": "decompose"},
    ),
]

# Column width for the splitter-name column — derived from registry so it
# automatically widens when new entries are added.
_NAME_W = max(len(name) for name, *_ in SPLITTER_REGISTRY)


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
    def effective_tokens(self) -> list[str]:
        """Tokens after applying word_filter (len > 1), same as search_client."""
        return [t for t in self.tokens if len(t) > 1]

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

    @property
    def avg_token_count(self) -> float:
        """Average number of effective tokens per query.

        Lower values indicate the splitter keeps compound words intact.
        """
        if not self.query_results:
            return 0.0
        total = sum(len(qr.effective_tokens) for qr in self.query_results)
        return total / len(self.query_results)

    @property
    def single_token_rate(self) -> float:
        """Fraction of queries resolved to exactly one effective token.

        Higher values indicate better compound-word handling.
        """
        if not self.query_results:
            return 0.0
        single = sum(1 for qr in self.query_results if len(qr.effective_tokens) == 1)
        return single / len(self.query_results)


# ---------------------------------------------------------------------------
# Build helper
# ---------------------------------------------------------------------------
def build_sphinx(
    splitter_type_value: str | None,
    output_dir: Path,
    extra_options: dict[str, str] | None = None,
) -> float:
    """Build Sphinx HTML with the given splitter type, return elapsed seconds."""
    sink = io.StringIO()
    if splitter_type_value is None:
        search_options: dict = {}
    else:
        search_options = {"type": splitter_type_value}
    if extra_options:
        search_options.update(extra_options)
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
def check_availability(class_path: str) -> tuple[bool, str]:
    """Check if a splitter class is importable without instantiating it."""
    try:
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        getattr(module, class_name)
        return True, ""
    except (ImportError, AttributeError) as exc:
        return False, str(exc)


def load_splitter(class_path: str, extra_options: dict[str, str] | None = None):
    """Import and instantiate a splitter class by its dotted path."""
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(dict(extra_options or {}))


# ---------------------------------------------------------------------------
# Main benchmark logic
# ---------------------------------------------------------------------------
def run_benchmark(exclude: list[str] | None = None) -> list[SplitterResult]:
    """Build Sphinx for each splitter, run all queries, and return results."""
    excluded = set(exclude or [])
    results: list[SplitterResult] = []

    for display_name, type_value, class_path, extra_options in SPLITTER_REGISTRY:
        if display_name in excluded:
            print(f"  [{display_name}] excluded by --exclude", flush=True)
            continue
        print(f"  [{display_name}] checking availability ...", flush=True)

        # Check splitter availability (import only, no instantiation)
        available, reason = check_availability(class_path)
        if not available:
            results.append(
                SplitterResult(
                    name=display_name,
                    available=False,
                    unavailable_reason=reason,
                )
            )
            print(f"    -> skipped: {reason}")
            continue

        result = SplitterResult(name=display_name, available=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "build"
            output_dir.mkdir()

            # Build (includes cold-start cost such as dict download)
            print("    building index ...", flush=True)
            try:
                result.build_time = build_sphinx(type_value, output_dir, extra_options)
            except Exception as exc:
                result.available = False
                result.unavailable_reason = f"build failed: {exc}"
                results.append(result)
                print(f"    -> build failed: {exc}")
                continue

            result.index_size = (output_dir / "searchindex.js").stat().st_size
            index = load_index(output_dir)

            # Instantiate splitter for query tokenization (dict already cached)
            splitter = load_splitter(class_path, extra_options)

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
    # widths: name | Build(s) | Index(B) | Precision | Recall | F1
    w = _NAME_W
    sep = w + 1 + 8 + 1 + 10 + 1 + 10 + 1 + 8 + 1 + 6  # = w + 47
    print("\n" + "=" * sep)
    print("SUMMARY")
    print("=" * sep)
    print(
        f"{'Splitter':<{w}} {'Build(s)':>8} {'Index(B)':>10}"
        f" {'Precision':>10} {'Recall':>8} {'F1':>6}"
    )
    print("-" * sep)
    for r in results:
        if not r.available:
            print(f"{r.name:<{w}}  N/A (unavailable)")
            continue
        print(
            f"{r.name:<{w}} {r.build_time:>8.2f} {r.index_size:>10,}"
            f" {r.precision:>9.1%} {r.recall:>7.1%} {r.f1:>5.1%}"
        )


def print_per_query(results: list[SplitterResult]) -> None:
    """Print per-query token and hit breakdown for each available splitter."""
    w = _NAME_W
    sep = w + 47  # matches print_summary
    print("\n" + "=" * sep)
    print("PER-QUERY BREAKDOWN")
    print("=" * sep)

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
            # prefix "[OK] " or "[NG] " is 5 chars; indent 2 → total 7 before name
            print(f"  [{status}] {r.name:<{w}}  tokens={qr.tokens}  found={qr.results}")


def print_simple(results: list[SplitterResult]) -> None:
    """Print compact output focused on search-tokenizer quality metrics.

    Shows only metrics that differentiate splitters as search tools:
    - Index size (smaller = less token noise)
    - Average effective tokens per query (fewer = better compound handling)
    - Single-token rate (higher = compound words kept intact)
    - Queries where splitters produce different tokenizations
    """
    available = [r for r in results if r.available and r.query_results]

    # widths: name | Build(s) | Index(B) | Avg tokens | Single-tok%
    w = _NAME_W
    sep = w + 1 + 8 + 1 + 10 + 1 + 11 + 1 + 11  # = w + 44
    print("\n" + "=" * sep)
    print("TOKENIZER QUALITY SUMMARY")
    print("=" * sep)
    print(
        f"{'Splitter':<{w}} {'Build(s)':>8} {'Index(B)':>10}"
        f" {'Avg tokens':>11} {'Single-tok%':>11}"
    )
    print("-" * sep)
    for r in results:
        if not r.available:
            print(f"{r.name:<{w}}  N/A (unavailable)")
            continue
        print(
            f"{r.name:<{w}} {r.build_time:>8.2f} {r.index_size:>10,}"
            f" {r.avg_token_count:>11.2f} {r.single_token_rate:>11.1%}"
        )

    if not available:
        return

    # --- Queries where splitters disagree on tokenization ---
    query_ids = [qr.query_id for qr in available[0].query_results]
    diverging = []
    for qid in query_ids:
        rows = {}
        for r in available:
            qr = next(x for x in r.query_results if x.query_id == qid)
            rows[r.name] = qr.effective_tokens
        token_variants = set(tuple(t) for t in rows.values())
        if len(token_variants) > 1:
            diverging.append((qid, rows))

    print(f"\n{'=' * sep}")
    print(f"TOKENIZATION DIFFERENCES  ({len(diverging)} / {len(query_ids)} queries)")
    print("=" * sep)
    if not diverging:
        print("All splitters produced identical tokenizations.")
        return

    sample_r = available[0]
    for qid, rows in diverging:
        sample_qr = next(x for x in sample_r.query_results if x.query_id == qid)
        print(f"\n{qid}: {sample_qr.query!r}  ({sample_qr.description})")
        for name, tokens in rows.items():
            print(f"  {name:<{w}} {tokens}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Entry point: run the full benchmark and print results."""
    parser = argparse.ArgumentParser(
        description="Benchmark Sphinx Japanese search splitters."
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="NAME",
        default=[],
        help="Splitter names to skip (matched against SPLITTER_REGISTRY[*][0]).",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help=(
            "Compact output: tokenizer quality metrics and diverging queries only."
            " Omits Precision/Recall/F1 and the full per-query breakdown."
        ),
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Sphinx Japanese Search Splitter Benchmark")
    print("=" * 70)
    print()

    results = run_benchmark(exclude=args.exclude)

    if args.simple:
        print_simple(results)
    else:
        print_summary(results)
        print_per_query(results)

    unavailable = [r for r in results if not r.available]
    if unavailable:
        print("\n--- Unavailable splitters ---")
        for r in unavailable:
            print(f"  {r.name}: {r.unavailable_reason}")


if __name__ == "__main__":
    main()
