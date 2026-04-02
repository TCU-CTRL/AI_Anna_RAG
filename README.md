# Anna Bot

部活向け Discord Bot。`/anna` コマンドで部内資料を RAG 検索し、マスコットキャラクター anna として回答します。

## 構成

```
bot/
  main.py          # Bot 起動・コマンド同期
  config.py        # 環境変数から設定を読み込み
  cogs/ask.py      # /anna コマンドハンドラ
  services/
    search.py      # Azure AI Search 検索サービス
    ai.py          # Azure AI Foundry 回答生成サービス
scripts/
  indexer.py       # 部内資料を AI Search にインデックス投入
.github/workflows/
  index-docs.yml   # 資料 push 時のインデックス自動更新
```

## 環境構築（Docker）

Docker を使えば Python や uv のインストールなしで開発・テスト・実行ができます。

### 前提条件

- Docker / Docker Compose
- Discord Bot トークン（[Developer Portal](https://discord.com/developers/applications) で取得）
- Azure AI Search リソース（Free Tier で可）
- Azure AI Foundry（Azure OpenAI）のデプロイメント（gpt-4o-mini 推奨）

### セットアップ

```bash
cp .env.example .env
# .env を編集して各値を設定
```

### テスト実行

```bash
docker compose run --rm test
```

### Bot 起動

```bash
docker compose up bot
```

### ローカル開発（Docker なし）

Python 3.12+ と [uv](https://docs.astral.sh/uv/) が必要です。

### セットアップ

```bash
# リポジトリをクローン
git clone <repository-url>
cd anna-bot

# 依存関係をインストール
uv sync

# 環境変数を設定
cp .env.example .env
# .env を編集して各値を設定
```

### 環境変数

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `DISCORD_TOKEN` | Yes | Discord Bot トークン |
| `DISCORD_GUILD_ID` | No | 開発用: Guild コマンドとして即時反映。空なら Global |
| `AZURE_SEARCH_ENDPOINT` | Yes | Azure AI Search のエンドポイント URL |
| `AZURE_SEARCH_API_KEY` | Yes | Azure AI Search の API キー（検索には Query Key、インデックス投入には Admin Key） |
| `AZURE_SEARCH_INDEX_NAME` | Yes | Azure AI Search のインデックス名 |
| `AZURE_OPENAI_ENDPOINT` | Yes | Azure OpenAI のエンドポイント URL |
| `AZURE_OPENAI_API_KEY` | Yes | Azure OpenAI の API キー |
| `AZURE_OPENAI_DEPLOYMENT` | Yes | デプロイメント名（例: `gpt-4o-mini`） |
| `AZURE_OPENAI_API_VERSION` | Yes | API バージョン（例: `2024-12-01-preview`） |

## Bot の起動

```bash
uv run python -m bot.main
```

起動すると Discord に接続し、`/anna` スラッシュコマンドが利用可能になります。

## Azure AI Search インデックスの作成

Azure Portal または REST API でインデックスを作成します。

```json
{
  "name": "anna-club-docs",
  "fields": [
    { "name": "id",        "type": "Edm.String", "key": true, "filterable": true },
    { "name": "title",     "type": "Edm.String", "searchable": true, "retrievable": true },
    { "name": "content",   "type": "Edm.String", "searchable": true, "retrievable": true, "analyzer": "ja.lucene" },
    { "name": "source",    "type": "Edm.String", "filterable": true, "retrievable": true },
    { "name": "category",  "type": "Edm.String", "filterable": true, "facetable": true, "retrievable": true }
  ]
}
```

## 資料のインデックス投入

### 手動実行

```bash
AZURE_SEARCH_ENDPOINT=https://... \
AZURE_SEARCH_API_KEY=... \
AZURE_SEARCH_INDEX_NAME=anna-club-docs \
DOCS_DIR=docs \
uv run python scripts/indexer.py
```

### GitHub Actions による自動更新

部の GitHub Organization の private リポジトリで、以下の GitHub Secrets を設定します：

- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_API_KEY`
- `AZURE_SEARCH_INDEX_NAME`

`.github/workflows/index-docs.yml` が `docs/` ディレクトリの Markdown ファイルが main ブランチに push されたときに自動実行されます。

## Discord Bot の設定

1. [Discord Developer Portal](https://discord.com/developers/applications) で新しいアプリケーションを作成
2. **Bot** セクションでトークンを取得し、`.env` の `DISCORD_TOKEN` に設定
3. **OAuth2 > URL Generator** で以下のスコープと権限を選択：
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Use Slash Commands`
4. 生成された URL でサーバーに Bot を招待

## テスト

```bash
# ユニットテスト
uv run pytest tests/ -v

# 統合テスト（Azure 環境変数が必要）
uv run pytest tests/test_integration.py -v
```
