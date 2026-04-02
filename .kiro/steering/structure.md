# Project Structure

## Organization Philosophy

責務分離を重視した層構成。以下の 3 つの責務を明確に分ける:

1. **Discord 層**: ユーザー入出力、スラッシュコマンド処理、Discord API とのやりとり
2. **RAG 層**: Azure AI Search との連携、ドキュメント検索、出典情報の管理
3. **AI 層**: Azure AI Foundry との連携、プロンプト構築、回答生成

## Directory Patterns

### 設定・環境管理
**Purpose**: 環境変数、シークレット参照、接続情報を一元管理
**Pattern**: `.env` ファイルや設定モジュールで管理。ソースコードに直書きしない

### ドキュメント管理
**Purpose**: 検索対象となる部内資料の管理方針
**Pattern**: 部の GitHub Organization の private リポジトリをソースとし、Azure AI Search でインデックス

### 仕様管理
**Location**: `.kiro/specs/`
**Purpose**: 機能ごとの要件・設計・タスクを Spec-Driven Development で管理

## Naming Conventions

- 設計フェーズで確定（バックエンド言語選定後に決定）

## Code Organization Principles

- Discord Bot のイベントハンドリングと AI 呼び出しロジックを分離
- 検索ロジック（RAG）と回答生成ロジック（AI）を分離
- エラーハンドリングはユーザー向け応答と開発者向けログを分けて設計
- 設定値は環境変数から読み込み、ハードコードしない
- MVP では最小構成を維持し、不要な抽象化を避ける

---
_Document patterns, not file trees. New files following patterns shouldn't require updates_
