# Technology Stack

## Architecture

Discord Bot → バックエンド → Azure AI Foundry + Azure AI Search の 3 層構成。
責務分離: Discord 側（入出力）、Azure 側（AI 推論・検索）、RAG 側（検索・ドキュメント管理）を明確に分ける。

## Core Technologies

- **クラウド**: Azure（AI Foundry プロジェクト、AI Search）
- **AI 推論**: Azure AI Foundry（チャット補完 API）
- **検索基盤**: Azure AI Search（部の Organization の private リポジトリをインデックス）
- **Bot フレームワーク**: Discord Bot（スラッシュコマンド `/anna`）
- **バックエンド**: 実装容易性と保守性を優先（具体的なランタイム・フレームワークは設計フェーズで決定）

## RAG パイプライン

- 検索ソース: 部の GitHub Organization の private リポジトリ内テキスト資料
- 検索結果を踏まえて回答を生成（検索結果が不十分な場合は推測で断定しない）
- ソースのタイトル・出典を返せる設計
- 管理者がドキュメントを追加・更新しやすい構成

## Key Technical Decisions

| 決定事項 | 理由 |
|---------|------|
| Azure AI Foundry 経由で推論 | プロジェクト統合管理、学生向け利用を想定 |
| Azure AI Search を RAG 基盤に | マネージドサービスでインフラ管理を最小化 |
| テキスト資料から開始 | MVP の速度優先、画像・PDF の高度処理は後回し |
| 環境変数による設定管理 | シークレットをコードに含めない、環境差異の吸収 |

## 非機能要件方針

- **コスト**: 学生開発のため最小限。無料枠・小規模構成を優先
- **レスポンス**: Discord リクエストに数秒以内で一次応答
- **エラーハンドリング**: ユーザー向けメッセージと開発者向けログを分離
- **セキュリティ**: API キー・接続文字列は環境変数で管理、部外秘情報の外部漏洩防止

## Development Standards

### セキュリティ
- API キーや接続文字列をソースコードに直書きしない
- 認証・シークレット管理は必須
- Discord 上での権限・公開範囲を考慮

### コード品質
- 保守しやすい構成を重視
- README 整備
- 過剰に大規模な構成を避け、学生の個人開発〜小規模チーム運用として妥当な設計

---
_Document standards and patterns, not every dependency_
