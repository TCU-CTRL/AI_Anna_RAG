import pytest

from scripts.indexer import parse_markdown, chunk_document


class TestParseMarkdown:
    """Markdown パースのテスト"""

    def test_タイトルを最初のh1見出しから抽出する(self):
        md = "# 部活ルール\n\n本文です。"
        title, content = parse_markdown(md)
        assert title == "部活ルール"

    def test_h1がない場合はタイトルが空になる(self):
        md = "本文のみのファイル"
        title, content = parse_markdown(md)
        assert title == ""

    def test_本文からh1行が除去される(self):
        md = "# タイトル\n\n本文です。"
        title, content = parse_markdown(md)
        assert "# タイトル" not in content
        assert "本文です。" in content


class TestChunkDocument:
    """ドキュメントチャンキングのテスト"""

    def test_h2見出しで分割される(self):
        md = "# メイン\n\n## セクション1\n内容1\n\n## セクション2\n内容2"
        chunks = chunk_document(md, "docs/test.md")

        assert len(chunks) == 2
        assert "内容1" in chunks[0]["content"]
        assert "内容2" in chunks[1]["content"]

    def test_各チャンクに元ドキュメントのタイトルとソースが保持される(self):
        md = "# ルール集\n\n## ルール1\n詳細1\n\n## ルール2\n詳細2"
        chunks = chunk_document(md, "docs/rules.md")

        for chunk in chunks:
            assert chunk["title"] == "ルール集"
            assert chunk["source"] == "docs/rules.md"

    def test_チャンクIDがファイルパスとセクションから生成される(self):
        md = "# タイトル\n\n## セクションA\n内容A"
        chunks = chunk_document(md, "docs/test.md")

        assert chunks[0]["id"] is not None
        assert len(chunks[0]["id"]) > 0

    def test_h2がない場合は文書全体が1チャンクになる(self):
        md = "# タイトル\n\n本文のみの資料です。分割する見出しがありません。"
        chunks = chunk_document(md, "docs/simple.md")

        assert len(chunks) == 1
        assert "本文のみの資料" in chunks[0]["content"]

    def test_空ファイルは空リストを返す(self):
        chunks = chunk_document("", "docs/empty.md")
        assert chunks == []

    def test_チャンクにcategoryフィールドが含まれる(self):
        md = "# タイトル\n\n## セクション\n内容"
        chunks = chunk_document(md, "docs/rules/guide.md")

        for chunk in chunks:
            assert "category" in chunk
