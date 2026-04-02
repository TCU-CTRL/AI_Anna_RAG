# Requirements Document

## Introduction
本ドキュメントは、部活向け Discord Bot「anna」の `/anna` コマンドによる部内質問応答機能の要件を定義する。部員が Discord 上で `/anna` スラッシュコマンドを使い、部内資料を RAG で検索して、マスコットキャラクター anna として自然な日本語で回答を生成する MVP 機能を対象とする。

## Requirements

### Requirement 1: スラッシュコマンドによる質問受付
**Objective:** 部員として、Discord 上で `/anna` コマンドを使って自然言語で質問したい。気軽に部の情報を確認できるようにするため。

#### Acceptance Criteria
1. When 部員が Discord サーバーで `/anna` コマンドを実行する, the Anna Bot shall 質問文を入力するためのテキスト入力パラメータを表示する
2. When 部員が `/anna` コマンドに質問文を入力して送信する, the Anna Bot shall 3秒以内に「考え中」の一次応答（Deferred Response）を返す
3. When 一次応答の送信後, the Anna Bot shall バックエンドで質問処理を開始し、回答生成完了後に一次応答を最終回答で更新する
4. If 質問文が空または未入力の場合, the Anna Bot shall 質問文の入力を促すメッセージを返す

### Requirement 2: RAG による部内資料検索
**Objective:** 部員として、質問に関連する部内資料を自動で検索してほしい。正確な情報に基づいた回答を得るため。

**前提:** 検索ソースは部の GitHub Organization の private リポジトリ内テキスト資料（Markdown 等）とする。GitHub Actions と Azure AI Search の Push API を使用してインデックスに投入し、追加の Azure リソース（Blob Storage 等）を不要とする構成で、コストを最小化する。

#### Acceptance Criteria
1. When 質問文を受信する, the Anna Bot shall Azure AI Search に対してクエリを送信し、関連する部内資料を検索する
2. When 検索結果が返される, the Anna Bot shall 関連度の高い上位ドキュメントを回答生成のコンテキストとして使用する
3. When 検索結果に該当する資料が見つからない, the Anna Bot shall 検索結果なしの状態を回答生成に伝え、資料が見つからなかった旨を含む回答を生成する
4. The Anna Bot shall 検索クエリに API キーや接続文字列をソースコードに含めず、環境変数で管理する
5. When 部の GitHub リポジトリに資料が push される, the GitHub Actions ワークフロー shall リポジトリ内のテキスト資料を解析し、Azure AI Search の Push API でインデックスを更新する

### Requirement 3: LLM による回答生成
**Objective:** 部員として、検索結果に基づいた正確でわかりやすい回答を受け取りたい。資料を自分で探す手間を省くため。

#### Acceptance Criteria
1. When 検索結果のコンテキストが準備される, the Anna Bot shall Azure AI Foundry のチャット補完 API を使用して回答を生成する
2. When 回答を生成する, the Anna Bot shall 検索結果の内容を根拠として使用し、根拠のない情報を断定しない
3. When 検索結果が不十分で回答に十分な根拠がない場合, the Anna Bot shall 「資料に該当する情報が見つかりませんでした」という趣旨の回答を生成する
4. When 回答の根拠となる資料がある場合, the Anna Bot shall 回答に参照元の資料タイトルまたは出典情報を含める

### Requirement 4: キャラクター性のある応答
**Objective:** 部員として、単なる機械的な回答ではなく、部のマスコットキャラクター anna らしい親しみやすい応答を受け取りたい。部の一体感やコミュニケーション文化を育むため。

#### Acceptance Criteria
1. The Anna Bot shall 親しみやすく、丁寧で、軽くかわいげのある口調で回答を生成する
2. The Anna Bot shall 情報の正確性を最優先し、キャラクター性のために事実を歪めない
3. When 回答が部内資料に基づく場合, the Anna Bot shall 必要に応じて「部内資料に基づく回答」であることを示す
4. The Anna Bot shall 全ての回答において一貫したキャラクターの口調を維持する

### Requirement 5: エラーハンドリング
**Objective:** 部員として、エラーが発生した場合でもわかりやすいメッセージを受け取りたい。Bot が無言で失敗して混乱することを避けるため。

#### Acceptance Criteria
1. If Azure AI Search への接続に失敗した場合, the Anna Bot shall ユーザーに「一時的に回答できません」という趣旨のメッセージを返す
2. If Azure AI Foundry への API 呼び出しに失敗した場合, the Anna Bot shall ユーザーに「回答の生成に失敗しました」という趣旨のメッセージを返す
3. If 予期しないエラーが発生した場合, the Anna Bot shall ユーザーにわかりやすいエラーメッセージを返し、内部エラーの詳細をユーザーに公開しない
4. If いずれかのエラーが発生した場合, the Anna Bot shall エラーの詳細（スタックトレース、リクエスト情報、タイムスタンプ）を開発者向けログに記録する

### Requirement 6: ログ記録
**Objective:** 開発者として、Bot の動作状況を把握し問題を迅速に調査したい。運用品質を維持するため。

#### Acceptance Criteria
1. When 質問を受信する, the Anna Bot shall リクエストの基本情報（タイムスタンプ、ユーザー識別子、質問文の有無）をログに記録する
2. When 回答を生成する, the Anna Bot shall 処理時間と回答のステータス（成功/失敗）をログに記録する
3. The Anna Bot shall ユーザー向けメッセージと開発者向けログを分離し、内部情報がユーザーに漏洩しない設計にする
4. The Anna Bot shall ログに API キーや接続文字列などの機密情報を出力しない

### Requirement 7: セキュリティ
**Objective:** 管理者として、部外秘の情報やシステムの認証情報が外部に漏洩しないようにしたい。部の情報資産とシステムの安全性を守るため。

#### Acceptance Criteria
1. The Anna Bot shall API キー、接続文字列、トークン等のシークレットを環境変数で管理し、ソースコードに含めない
2. The Anna Bot shall Discord Bot トークンおよび Azure の認証情報を安全に管理する
3. The Anna Bot shall 部内資料の検索結果を、Bot が動作している Discord サーバー内の応答にのみ使用する
4. The Anna Bot shall エラーメッセージやログ出力に内部システムの詳細（接続先 URL、内部 IP 等）をユーザーに公開しない

### Requirement 8: 運用・保守性
**Objective:** 管理者として、Bot の設定変更や資料の追加を簡単に行いたい。長期的に運用しやすいシステムにするため。

#### Acceptance Criteria
1. The Anna Bot shall 接続先やモデル名などの設定を環境変数で外部化し、コード変更なしで切り替え可能にする
2. The Anna Bot shall Azure AI Search のインデックスに新しい資料を追加することで、検索対象を拡張できる設計にする
3. The Anna Bot shall README に環境構築手順、環境変数の説明、デプロイ手順を記載する

## MVP 対象外（将来拡張）
以下は本要件の対象外とし、将来の拡張として扱う：
- 画像・音声の入力対応
- 管理画面の構築
- 高度なアクセス制御・権限管理
- 部員ごとの個人化・パーソナライズ
- 会話履歴に基づく長期記憶
- PDF・画像ドキュメントの高度な解析
