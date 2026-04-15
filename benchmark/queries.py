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
    # --- history ---
    {
        "id": "q09",
        "query": "幕府",
        "description": "2文字複合語（歴史用語）",
        "expected": ["history"],
        "not_expected": ["food", "technology", "sports"],
    },
    {
        "id": "q10",
        "query": "明治維新",
        "description": "4文字複合語（歴史用語）",
        "expected": ["history"],
        "not_expected": ["food", "sports", "economy"],
    },
    {
        "id": "q11",
        "query": "戦国時代",
        "description": "4文字複合語（時代名）",
        "expected": ["history"],
        "not_expected": ["food", "sports", "nature"],
    },
    {
        "id": "q12",
        "query": "参勤交代",
        "description": "4文字複合語（制度名）",
        "expected": ["history"],
        "not_expected": ["food", "technology", "sports"],
    },
    # --- nature ---
    {
        "id": "q13",
        "query": "地球温暖化",
        "description": "5文字複合語（環境用語）",
        "expected": ["nature"],
        "not_expected": ["food", "sports", "history"],
    },
    {
        "id": "q14",
        "query": "生態系",
        "description": "3文字複合語（環境用語）",
        "expected": ["nature"],
        "not_expected": ["food", "sports", "economy"],
    },
    {
        "id": "q15",
        "query": "絶滅危惧種",
        "description": "5文字複合語（環境用語）",
        "expected": ["nature"],
        "not_expected": ["food", "technology", "history"],
    },
    # --- medicine ---
    {
        "id": "q16",
        "query": "ワクチン",
        "description": "カタカナ語（医療用語）",
        "expected": ["medicine"],
        "not_expected": ["food", "sports", "economy"],
    },
    {
        "id": "q17",
        "query": "新型コロナウイルス",
        "description": "長い複合語（感染症名）",
        "expected": ["medicine"],
        "not_expected": ["food", "technology", "sports"],
    },
    {
        "id": "q18",
        "query": "免疫",
        "description": "2文字複合語（医療用語）",
        "expected": ["medicine"],
        "not_expected": ["food", "sports", "history"],
    },
    {
        "id": "q19",
        "query": "生活習慣病",
        "description": "5文字複合語（疾患カテゴリ）",
        "expected": ["medicine"],
        "not_expected": ["food", "sports", "economy"],
    },
    # --- economy ---
    {
        "id": "q20",
        "query": "株式市場",
        "description": "4文字複合語（経済用語）",
        "expected": ["economy"],
        "not_expected": ["food", "sports", "history"],
    },
    {
        "id": "q21",
        "query": "インフレーション",
        "description": "カタカナ語（経済用語）",
        "expected": ["economy"],
        "not_expected": ["food", "sports", "medicine"],
    },
    {
        "id": "q22",
        "query": "国際貿易",
        "description": "4文字複合語（経済用語）",
        "expected": ["economy"],
        "not_expected": ["food", "sports", "history"],
    },
    # --- arts ---
    {
        "id": "q23",
        "query": "茶道",
        "description": "2文字複合語（伝統芸能）",
        "expected": ["arts"],
        "not_expected": ["food", "sports", "history"],
    },
    {
        "id": "q24",
        "query": "浮世絵",
        "description": "3文字複合語（視覚芸術）",
        "expected": ["arts"],
        "not_expected": ["food", "technology", "sports"],
    },
    {
        "id": "q25",
        "query": "アニメーション",
        "description": "カタカナ語（ポップカルチャー）",
        "expected": ["arts"],
        "not_expected": ["food", "sports", "economy"],
    },
    {
        "id": "q26",
        "query": "俳句",
        "description": "2文字複合語（文学形式）",
        "expected": ["arts"],
        "not_expected": ["food", "technology", "sports"],
    },
    # --- science ---
    {
        "id": "q27",
        "query": "量子力学",
        "description": "4文字複合語（物理学）",
        "expected": ["science"],
        "not_expected": ["food", "sports", "history"],
    },
    {
        "id": "q28",
        "query": "相対性理論",
        "description": "5文字複合語（物理学）",
        "expected": ["science"],
        "not_expected": ["food", "sports", "medicine"],
    },
    {
        "id": "q29",
        "query": "元素周期表",
        "description": "5文字複合語（化学）",
        "expected": ["science"],
        "not_expected": ["food", "sports", "history"],
    },
    {
        "id": "q30",
        "query": "素粒子",
        "description": "3文字複合語（物理学）",
        "expected": ["science"],
        "not_expected": ["food", "sports", "economy"],
    },
    # --- travel ---
    {
        "id": "q31",
        "query": "温泉",
        "description": "2文字複合語（観光資源）",
        "expected": ["travel"],
        "not_expected": ["food", "technology", "sports"],
    },
    {
        "id": "q32",
        "query": "富士山",
        "description": "3文字の固有名詞",
        "expected": ["travel"],
        "not_expected": ["food", "technology", "sports"],
    },
]
