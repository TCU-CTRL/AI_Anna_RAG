"""部内資料を Azure AI Search にインデックス投入するスクリプト。

GitHub Actions から呼び出され、リポジトリ内の Markdown ファイルを
パース・チャンク分割し、Push API でインデックスに投入する。
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

import requests


def parse_markdown(text: str) -> tuple[str, str]:
    """Markdown テキストからタイトル（最初の h1）と本文を抽出する。"""
    title = ""
    lines = text.split("\n")
    content_lines = []

    for line in lines:
        if not title and re.match(r"^#\s+", line):
            title = re.sub(r"^#\s+", "", line).strip()
        else:
            content_lines.append(line)

    content = "\n".join(content_lines).strip()
    return title, content


def chunk_document(text: str, file_path: str) -> list[dict]:
    """Markdown ドキュメントを h2 見出し単位でチャンクに分割する。"""
    if not text.strip():
        return []

    title, content = parse_markdown(text)
    category = str(Path(file_path).parent)

    # h2 で分割
    sections = re.split(r"(?=^##\s+)", content, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    if not sections:
        doc_id = hashlib.md5(file_path.encode()).hexdigest()
        return [
            {
                "id": doc_id,
                "title": title or Path(file_path).stem,
                "content": content,
                "source": file_path,
                "category": category,
            }
        ]

    chunks = []
    for i, section in enumerate(sections):
        section_id = hashlib.md5(f"{file_path}:{i}".encode()).hexdigest()
        chunks.append(
            {
                "id": section_id,
                "title": title or Path(file_path).stem,
                "content": section,
                "source": file_path,
                "category": category,
            }
        )

    return chunks


def push_to_search(chunks: list[dict], endpoint: str, api_key: str, index_name: str) -> None:
    """Azure AI Search の Push API でドキュメントをインデックスに投入する。"""
    if not chunks:
        return

    url = f"{endpoint}/indexes/{index_name}/docs/index?api-version=2024-07-01"
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    documents = []
    for chunk in chunks:
        doc = {"@search.action": "mergeOrUpload", **chunk}
        documents.append(doc)

    # バッチ制限: 1000 docs per request
    batch_size = 1000
    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        body = {"value": batch}
        resp = requests.post(url, json=body, headers=headers)
        resp.raise_for_status()
        print(f"  投入完了: {len(batch)} docs")


def main() -> None:
    """メインエントリーポイント。環境変数から設定を読み込み、Markdown ファイルを処理する。"""
    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    api_key = os.environ["AZURE_SEARCH_API_KEY"]
    index_name = os.environ["AZURE_SEARCH_INDEX_NAME"]
    docs_dir = os.environ.get("DOCS_DIR", "docs")

    docs_path = Path(docs_dir)
    if not docs_path.exists():
        print(f"ドキュメントディレクトリが見つかりません: {docs_dir}")
        sys.exit(1)

    md_files = list(docs_path.rglob("*.md"))
    if not md_files:
        print("Markdown ファイルが見つかりません")
        return

    all_chunks: list[dict] = []
    for md_file in md_files:
        print(f"処理中: {md_file}")
        text = md_file.read_text(encoding="utf-8")
        rel_path = str(md_file.relative_to(docs_path.parent))
        chunks = chunk_document(text, rel_path)
        all_chunks.extend(chunks)

    print(f"合計 {len(all_chunks)} チャンクを投入します")
    push_to_search(all_chunks, endpoint, api_key, index_name)
    print("インデックス更新完了")


if __name__ == "__main__":
    main()
