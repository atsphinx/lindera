"""Test cases for atsphinx.lindera.splitter."""

from __future__ import annotations

from importlib import metadata

import platformdirs
import pytest
from atsphinx.lindera import splitter as t


def test_diff_by_splitters():
    """This case tests difference from other splitters."""
    from sphinx.search.ja import DefaultSplitter

    default_splitter = DefaultSplitter({})
    lindera_splitter = t.LinderaSplitter({})
    text = "関西国際空港"
    assert default_splitter.split(text) == ["関西国際", "空港"]
    assert lindera_splitter.split(text) == ["関西国際空港"]


@pytest.mark.parametrize(
    "text,tokens",
    [
        ("関西国際空港", ["関西国際空港"]),
    ],
)
def test_tokenize(text: str, tokens: list[str]):
    splitter = t.LinderaSplitter({})
    assert splitter.split(text) == tokens


@pytest.mark.parametrize(
    "dict_type", ["ipadic", "ipadic-neologd", "cc-cedict", "jieba", "ko-dic", "unidic"]
)
def test_dictionary(dict_type: str):
    lindera_version = metadata.version("lindera-python")
    cache_base_dir = platformdirs.user_cache_path("atsphinx-lindera")
    sys_dict = t.SystemDictionary.init(dict_type)  # ty: ignore[invalid-argument-type]
    assert (
        sys_dict.local_path
        == cache_base_dir / "_dict" / lindera_version / f"lindera-{dict_type}"
    )
    sys_dict.fetch()
    assert sys_dict.local_path.exists()
