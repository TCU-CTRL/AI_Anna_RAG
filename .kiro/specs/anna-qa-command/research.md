# Research & Design Decisions

## Summary
- **Feature**: `anna-qa-command`
- **Discovery Scope**: New Feature（グリーンフィールド）
- **Key Findings**:
  - discord.py v2.x の `app_commands` + Deferred Response パターンが最適。3秒以内に defer し、15分以内に回答を返す
  - Azure AI Search Free Tier（10,000 docs / 50MB）は MVP に十分。Push API で GitHub Actions から直接インデックス投入可能
  - gpt-4o-mini が最もコスト効率が高い（入力 $0.15/1M tokens）。openai SDK の `AzureOpenAI` クラスで統一的にアクセス可能

## Research Log

### Discord Bot ライブラリとインタラクションパターン
- **Context**: Discord スラッシュコマンドの実装方法と Deferred Response の仕組みを調査
- **Sources Consulted**: discord.py v2.x 公式ドキュメント、Discord API ドキュメント
- **Findings**:
  - **discord.py v2.x** が Python での標準ライブラリ。`app_commands` モジュールでスラッシュコマンドをサポート
  - Deferred Response: `interaction.response.defer(thinking=True)` で「考え中」状態を表示
  - 初回応答期限: **3秒**、インタラクショントークン有効期限: **15分**
  - メッセージ長制限: content **2000文字**、Embed description **4096文字**
  - 開発中は Guild コマンド（即時反映）、本番は Global コマンドを使用
- **Implications**: RAG + LLM の処理時間は通常数秒〜十数秒なので、15分のトークン有効期限内に十分収まる。長い回答は Embed を活用

### Azure AI Search Push API とインデックス設計
- **Context**: GitHub リポジトリから Azure AI Search への資料投入方法を調査
- **Sources Consulted**: Azure AI Search REST API ドキュメント
- **Findings**:
  - Push API エンドポイント: `POST https://<service>.search.windows.net/indexes/<index>/docs/index?api-version=2024-07-01`
  - 認証: Admin API Key（書き込み用）、Query API Key（読み取り用）
  - バッチ制限: 1リクエストあたり 1,000 docs または 16MB
  - Free Tier: インデックス 3個、ドキュメント 10,000件、ストレージ 50MB、SLA なし
  - 日本語テキストには `ja.lucene` アナライザーを使用
  - Free Tier ではセマンティックランキング不可 → Keyword (BM25) 検索で開始
  - `mergeOrUpload` アクションで既存ドキュメントの更新も対応
- **Implications**: Free Tier の制限は部内資料規模なら十分。ベクトル検索は embedding モデルの追加コストが発生するため、MVP では BM25 キーワード検索から開始し、必要に応じてハイブリッド検索に拡張

### Azure AI Foundry チャット補完 API
- **Context**: RAG の回答生成に使用する LLM API を調査
- **Sources Consulted**: Azure OpenAI Service ドキュメント、openai SDK ドキュメント
- **Findings**:
  - エンドポイント: `https://<resource>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=2024-12-01-preview`
  - SDK: `openai` パッケージの `AzureOpenAI` クラス（Python）。非同期は `AsyncAzureOpenAI`
  - gpt-4o-mini: 128K コンテキスト、入力 $0.15/1M tokens、出力 $0.60/1M tokens
  - RAG コンテキストはシステムメッセージに埋め込む方式が標準
  - "On Your Data" 機能で Azure AI Search を直接データソースとして統合可能だが、制御性が低い
  - `temperature=0.3` 程度で事実ベースの回答精度を向上
- **Implications**: DIY RAG（手動で検索結果をプロンプトに埋め込む）方式を採用。制御性が高く、Free Tier の AI Search と組み合わせやすい

### Python バックエンド構成
- **Context**: Discord Bot のバックエンド構成とプロジェクト構造を調査
- **Sources Consulted**: discord.py ベストプラクティス、Python プロジェクト構成ガイド
- **Findings**:
  - discord.py を単一プロセスとして実行し、Web サーバー（FastAPI 等）は不要
  - aiohttp は discord.py の依存関係として既に含まれている → 追加インストール不要
  - Cogs パターンでコマンドハンドラをモジュール化
  - Services レイヤーで外部 API ロジックを分離
  - Python 3.11-3.12 + uv（パッケージマネージャー）推奨
- **Implications**: 最小構成で `bot/main.py` + `bot/cogs/` + `bot/services/` の 3 層構造。Web サーバーなしでシンプルに保つ

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Layered（採用） | Discord 層 / RAG 層 / AI 層の 3 層分離 | シンプル、理解しやすい、学生向け | 層間の依存が密になりやすい | Steering の責務分離方針と一致 |
| Hexagonal | Ports & Adapters による抽象化 | テスタビリティが高い、交換容易 | MVP には過剰な抽象化 | 将来の拡張時に検討 |
| Event-Driven | イベントバスによる疎結合 | 拡張性が高い | 学生プロジェクトには複雑すぎる | 不採用 |

## Design Decisions

### Decision: バックエンド言語として Python を採用
- **Context**: 実装容易性と保守性を優先するバックエンド言語の選定
- **Alternatives Considered**:
  1. Python — discord.py、openai SDK が成熟、学生に馴染みやすい
  2. Node.js/TypeScript — discord.js、型安全だが学習コストが高い
- **Selected Approach**: Python 3.12 + discord.py v2.x
- **Rationale**: discord.py と openai SDK が両方 Python で成熟しており、学生開発チームの学習コストが最も低い。aiohttp が discord.py に同梱されているため依存関係も最小
- **Trade-offs**: 型安全性は TypeScript に劣るが、type hints で補完可能
- **Follow-up**: Python 3.12 の動作確認、uv によるプロジェクト初期化

### Decision: MVP では BM25 キーワード検索を採用
- **Context**: Azure AI Search の検索方式選定
- **Alternatives Considered**:
  1. BM25 キーワード検索 — Free Tier 対応、追加コストなし
  2. ベクトル検索 — embedding モデルのコストが発生
  3. ハイブリッド検索 + セマンティックランキング — Basic Tier 以上が必要（月額 $75+）
- **Selected Approach**: BM25 キーワード検索（Free Tier）
- **Rationale**: コスト最小化が最優先。日本語 `ja.lucene` アナライザーで十分な検索品質を確保。部内資料は専門用語が限られており、キーワード検索で実用的な精度が期待できる
- **Trade-offs**: 意味的な類似検索は不可。将来ベクトル検索への拡張パスは確保
- **Follow-up**: 検索品質が不十分な場合はベクトル検索への移行を検討

### Decision: DIY RAG（手動プロンプト埋め込み）を採用
- **Context**: RAG パイプラインの実装方式
- **Alternatives Considered**:
  1. DIY RAG — 検索結果をシステムメッセージに手動埋め込み
  2. On Your Data — Azure AI Foundry の組み込み RAG 機能
- **Selected Approach**: DIY RAG
- **Rationale**: 制御性が高く、プロンプト設計（キャラクター口調の制御）を柔軟にカスタマイズ可能。Free Tier の AI Search と直接組み合わせられる
- **Trade-offs**: 検索→プロンプト構築のコードを自前で実装する必要がある
- **Follow-up**: 出典情報のフォーマット設計

## Risks & Mitigations
- **Free Tier の制限超過** — ドキュメント数・ストレージのモニタリングを設定し、閾値アラートで事前検知
- **Discord の 3 秒応答期限** — 必ず defer を最初に呼び出す設計パターンを強制
- **LLM のハルシネーション** — システムプロンプトで「検索結果のみに基づいて回答」を明示し、temperature を低く設定
- **API キーの漏洩** — .env ファイルと環境変数で管理、.gitignore に .env を含める

## References
- discord.py v2.x ドキュメント — スラッシュコマンド、Cogs、非同期パターン
- Azure AI Search REST API (2024-07-01) — Push API、インデックス設計、アナライザー
- Azure OpenAI Service — gpt-4o-mini デプロイメント、チャット補完 API
- openai Python SDK v1.x — AzureOpenAI / AsyncAzureOpenAI クラス
