"""Test queries with relevance judgments for benchmark evaluation."""

from __future__ import annotations

# Each query defines:
#   query: search string
#   description: human-readable note about what is being tested
#   expected: document names that MUST appear in results
#   not_expected: document names that MUST NOT appear in results
QUERIES: list[dict] = [
    {
        "id": "q01",
        "query": "寿司",
        "description": "単純な名詞",
        "expected": ["food"],
        "not_expected": ["technology", "sports"],
    },
    {
        "id": "q02",
        "query": "ラーメン",
        "description": "カタカナ語",
        "expected": ["food"],
        "not_expected": ["technology", "sports"],
    },
    {
        "id": "q03",
        "query": "野球",
        "description": "2文字の複合語",
        "expected": ["sports"],
        "not_expected": ["food", "technology"],
    },
    {
        "id": "q04",
        "query": "機械学習",
        "description": "複合語（技術用語）",
        "expected": ["technology"],
        "not_expected": ["food", "sports"],
    },
    {
        "id": "q05",
        "query": "人工知能",
        "description": "複合語（AI用語）",
        "expected": ["technology"],
        "not_expected": ["food", "sports"],
    },
    {
        "id": "q06",
        "query": "自然言語処理",
        "description": "長い複合語",
        "expected": ["technology"],
        "not_expected": ["food", "sports"],
    },
    {
        "id": "q07",
        "query": "ディープラーニング",
        "description": "カタカナの専門用語",
        "expected": ["technology"],
        "not_expected": ["food", "sports"],
    },
    {
        "id": "q08",
        "query": "サッカー",
        "description": "カタカナのスポーツ名",
        "expected": ["sports"],
        "not_expected": ["food", "technology"],
    },
]
