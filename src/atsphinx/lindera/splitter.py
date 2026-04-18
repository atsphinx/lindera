"""Splitter for default search.

This module provides custom splitter for ``html_search_options``.

When you want to this, you should set into your ``conf.py``.

.. code:: python

   html_search_options = {
       "type": "atsphinx.lindera.splitter.LinderaSplitter"
   }
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import platformdirs
import requests
from sphinx.search.ja import BaseSplitter

from lindera import TokenizerBuilder  # ty: ignore[unresolved-import]

if TYPE_CHECKING:
    from lindera import Tokenizer  # ty: ignore[unresolved-import]

RELEASED_DICT_TYPE = Literal[
    "ipadic", "ipadic-neologd", "cc-cedict", "jieba", "ko-dic", "unidic"
]


@dataclass
class SplitterOptions:
    """Option struct for splitter object."""

    mode: Literal["normal", "decompose"] = "normal"
    """Tokenize mode."""
    dict_type: RELEASED_DICT_TYPE = "ipadic"
    """Type of system dictionary."""

    @classmethod
    def from_dict(cls, options: dict[str, str]) -> "SplitterOptions":
        """Create object from options dict of sphinx configuration."""
        if "type" in options:
            del options["type"]
        return cls(**options)  # ty: ignore[invalid-argument-type]


@dataclass
class SystemDictionary:
    """Handler for system dictionary of Lindera."""

    dict_type: RELEASED_DICT_TYPE
    version: str
    cache_dir: Path

    @property
    def local_path(self) -> Path:
        """Local fullpath of extracted system dictionary."""
        return self.cache_dir / self.version / f"lindera-{self.dict_type}"

    @classmethod
    def init(cls, dict_type: RELEASED_DICT_TYPE) -> "SystemDictionary":
        """Create object from dict-type."""
        version = metadata.version("lindera-python")
        dirs = platformdirs.PlatformDirs("atsphinx-lindera")
        cache_dir = dirs.user_cache_path / "_dict"
        return cls(dict_type=dict_type, version=version, cache_dir=cache_dir)

    def fetch(self) -> None:
        """Fetch dictionary files from publshed website.

        If it already downloaded, skip proccess.
        """
        if self.local_path.exists():
            return
        url = f"https://github.com/lindera/lindera/releases/download/v{self.version}/lindera-{self.dict_type}-{self.version}.zip"
        dest = self.local_path.parent
        dest.mkdir(exist_ok=True, parents=True)
        with (
            requests.get(url, allow_redirects=True) as res,
            io.BytesIO(res.content) as bytes_io,
            zipfile.ZipFile(bytes_io) as zip,
        ):
            zip.extractall(dest)


class LinderaSplitter(BaseSplitter):
    """Simple splitter class using Lindera as tokeniser."""

    def __init__(self, options: dict[str, str]) -> None:  # noqa: D107
        options_ = SplitterOptions.from_dict(options)
        dict_ = SystemDictionary.init(options_.dict_type)
        dict_.fetch()
        self.tokenizer: Tokenizer = (
            TokenizerBuilder()
            .set_mode(options_.mode)
            .set_dictionary(str(dict_.local_path))
            .build()
        )

    def split(self, input: str) -> list[str]:  # noqa: D102
        return [token.surface for token in self.tokenizer.tokenize(input)]
