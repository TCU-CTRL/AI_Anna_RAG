"""統合テスト — 実際の Azure / Gemini サービスへの接続確認。

環境変数が設定されている場合のみ実行される。
実行方法: uv run pytest tests/test_integration.py -v
"""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.config import Config

requires_azure_search = pytest.mark.skipif(
    not os.environ.get("AZURE_SEARCH_ENDPOINT"),
    reason="Azure AI Search の環境変数が未設定",
)

requires_gemini = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="Gemini の環境変数が未設定",
)

requires_all = pytest.mark.skipif(
    not (os.environ.get("AZURE_SEARCH_ENDPOINT") and os.environ.get("GEMINI_API_KEY")),
    reason="Azure / Gemini の環境変数が未設定",
)


def get_config() -> Config:
    return Config.from_env()


@requires_azure_search
class TestSearchServiceIntegration:
    """SearchService → Azure AI Search の統合テスト"""

    @pytest.mark.asyncio
    async def test_検索クエリを送信して結果を取得できる(self):
        from bot.services.search import SearchService

        config = get_config()
        service = SearchService(config)

        try:
            results = await service.search("テスト", top=3)
            assert isinstance(results, list)
        finally:
            await service.close()

    @pytest.mark.asyncio
    async def test_存在しないキーワードで空の結果が返る(self):
        from bot.services.search import SearchService

        config = get_config()
        service = SearchService(config)

        try:
            results = await service.search("xyzzynonexistent12345", top=1)
            assert isinstance(results, list)
        finally:
            await service.close()


@requires_gemini
class TestAIServiceIntegration:
    """AIService → Gemini の統合テスト"""

    @pytest.mark.asyncio
    async def test_回答を生成できる(self):
        from bot.services.ai import AIService, GeneratedAnswer
        from bot.services.search import SearchResult

        config = get_config()
        service = AIService(config)

        results = [
            SearchResult(
                id="test-1",
                title="テスト資料",
                content="部活の練習は毎週火曜日の18時から行われます。",
                source="docs/test.md",
                score=1.0,
            ),
        ]

        answer = await service.generate("練習日はいつですか？", results)

        assert isinstance(answer, GeneratedAnswer)
        assert len(answer.content) > 0
        assert answer.has_sufficient_context is True

    @pytest.mark.asyncio
    async def test_検索結果なしで回答を生成できる(self):
        from bot.services.ai import AIService, GeneratedAnswer

        config = get_config()
        service = AIService(config)

        answer = await service.generate("存在しない情報について教えて", [])

        assert isinstance(answer, GeneratedAnswer)
        assert answer.has_sufficient_context is False
        assert len(answer.content) > 0


@requires_all
class TestEndToEndFlow:
    """検索 → 生成の E2E フロー"""

    @pytest.mark.asyncio
    async def test_検索から回答生成までの一連のフローが動作する(self):
        from bot.services.ai import AIService
        from bot.services.search import SearchService

        config = get_config()
        search_service = SearchService(config)
        ai_service = AIService(config)

        try:
            search_results = await search_service.search("テスト")
            answer = await ai_service.generate("テスト質問", search_results)

            assert len(answer.content) > 0
            assert isinstance(answer.sources, list)
        finally:
            await search_service.close()

    @pytest.mark.asyncio
    async def test_モックInteractionでAskCogが動作する(self):
        from bot.cogs.ask import AskCog
        from bot.services.ai import AIService
        from bot.services.search import SearchService

        config = get_config()
        search_service = SearchService(config)
        ai_service = AIService(config)

        cog = AskCog(MagicMock(), search_service, ai_service)

        interaction = MagicMock()
        interaction.response = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.user = MagicMock()
        interaction.user.id = 99999
        interaction.user.display_name = "統合テストユーザー"

        try:
            await cog.anna.callback(cog, interaction, "テスト質問")

            interaction.response.defer.assert_called_once_with(thinking=True)
            interaction.followup.send.assert_called_once()

            sent_content = (
                interaction.followup.send.call_args[1].get("content")
                or interaction.followup.send.call_args[0][0]
            )
            assert len(sent_content) > 0
        finally:
            await search_service.close()
