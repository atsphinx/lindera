========
Splitter
========

"Splitter" is class to split text for html searching in sphinx-build.
By using Lindera, you can improve the accuracy of full-text search for HTML.

Usage
=====

You need to set settings into :confval:`html_search_options` of your ``conf.py``.

.. code-block:: python
   :caption: Very simple example

   # Your conf.py
   html_search_options = {
       "type": "atsphinx.lindera.splitter.LinderaSplitter",
   }

When you write this settings, ``sphinx-build`` tokenizes Japanese text using Lindera.

Configuration
=============

:confval:`html_search_options` supports some options.

.. py:attribute:: mode
   :type: str

   Tokenize mode of Lindera.

   It accepts these:

   - `"normal" <https://lindera.github.io/lindera/concepts/tokenization.html#normal-mode>`_
   - `"decompose" <https://lindera.github.io/lindera/concepts/tokenization.html#decompose-mode>`_

.. py:attribute:: dict_type
   :type: str

   Type of using system dictionary.

   lindera-python on PyPI doesn't have dictionary.
   Therefore, you need to download dictionary asset.

   atsphinx-lindera downloads system dictionary from GitHub Releases of lindera.
   This value is which type do you download.

   Supported types are:

   - "ipadic"
   - "ipadic-neologd"
   - "cc-cedict"
   - "jieba"
   - "ko-dic"
   - "unidic"
