========
Splitter
========

"Splitter"はHTML検索のためにテキストを分割するクラスです。
Linderaを利用することで、HTMLビルダー利用時に全文検索の精度を向上させることができます。

使用方法
========

``conf.py`` の :confval:`html_search_options` に設定を追加する必要があります。

.. code-block:: python
   :caption: 最小構成の例

   # Your conf.py
   html_search_options = {
       "type": "atsphinx.lindera.splitter.LinderaSplitter",
   }

この設定を記述すると、 ``sphinx-build`` の実行時にLinderaを使って日本語テキストをトークン化します。

設定
====

:confval:`html_search_options` はいくつかのオプションをサポートしています。

.. py:attribute:: mode
   :type: str

   Linderaのトークナイズモード。

   以下の値を受け付けます：

   - `"normal" <https://lindera.github.io/lindera/concepts/tokenization.html#normal-mode>`_
   - `"decompose" <https://lindera.github.io/lindera/concepts/tokenization.html#decompose-mode>`_

.. py:attribute:: dict_type
   :type: str

   使用するシステム辞書の種類。

   PyPI上のlindera-pythonには辞書が含まれていません。
   そのため、辞書アセットをダウンロードする必要があります。

   atsphinx-linderaではlinderaのGitHub Releasesからシステム辞書をダウンロードします。
   この値はダウンロードする辞書の種類を指定します。

   サポートされている種類：

   - "ipadic"
   - "ipadic-neologd"
   - "cc-cedict"
   - "jieba"
   - "ko-dic"
   - "unidic"
