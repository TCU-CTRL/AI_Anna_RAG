import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.cogs.ask import AskCog
from bot.services.ai import GenerateError, GeneratedAnswer
from bot.services.search import SearchError, SearchResult


def make_interaction() -> MagicMock:
    """Discord Interaction のモックを作成する"""
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.id = 12345
    interaction.user.display_name = "テスト部員"
    return interaction


def make_search_results() -> list[SearchResult]:
    return [
        SearchResult(
            id="doc-1",
            title="部活ルール",
            content="練習は毎週火曜の18時から。",
            source="docs/rules.md",
            score=2.0,
        ),
    ]


def make_answer(
    content: str = "練習は毎週火曜の18時からだよ！",
    sources: list[str] | None = None,
    has_context: bool = True,
) -> GeneratedAnswer:
    return GeneratedAnswer(
        content=content,
        sources=sources or ["部活ルール"],
        has_sufficient_context=has_context,
    )


class TestAskCogOrchestration:
    """質問応答のオーケストレーションのテスト"""

    @pytest.mark.asyncio
    async def test_最初にdeferが呼ばれる(self):
        search_service = AsyncMock()
        search_service.search = AsyncMock(return_value=make_search_results())
        ai_service = AsyncMock()
        ai_service.generate = AsyncMock(return_value=make_answer())

        cog = AskCog(MagicMock(), search_service, ai_service)
        interaction = make_interaction()

        await cog.anna.callback(cog, interaction, "練習日はいつ？")

        interaction.response.defer.assert_called_once_with(thinking=True)

    @pytest.mark.asyncio
    async def test_検索サービスに質問文が渡される(self):
        search_service = AsyncMock()
        search_service.search = AsyncMock(return_value=make_search_results())
        ai_service = AsyncMock()
        ai_service.generate = AsyncMock(return_value=make_answer())

        cog = AskCog(MagicMock(), search_service, ai_service)
        interaction = make_interaction()

        await cog.anna.callback(cog, interaction, "練習日はいつ？")

        search_service.search.assert_called_once_with("練習日はいつ？")

    @pytest.mark.asyncio
    async def test_検索結果がAIサービスに渡される(self):
        results = make_search_results()
        search_service = AsyncMock()
        search_service.search = AsyncMock(return_value=results)
        ai_service = AsyncMock()
        ai_service.generate = AsyncMock(return_value=make_answer())

        cog = AskCog(MagicMock(), search_service, ai_service)
        interaction = make_interaction()

        await cog.anna.callback(cog, interaction, "練習日はいつ？")

        ai_service.generate.assert_called_once_with("練習日はいつ？", results)

    @pytest.mark.asyncio
    async def test_回答がfollowupで送信される(self):
        search_service = AsyncMock()
        search_service.search = AsyncMock(return_value=make_search_results())
        ai_service = AsyncMock()
        ai_service.generate = AsyncMock(return_value=make_answer(
            content="練習は火曜18時だよ！",
            sources=["部活ルール"],
        ))

        cog = AskCog(MagicMock(), search_service, ai_service)
        interaction = make_interaction()

        await cog.anna.callback(cog, interaction, "練習日はいつ？")

        interaction.followup.send.assert_called_once()
        sent_content = interaction.followup.send.call_args[1].get("content") or interaction.followup.send.call_args[0][0]
        assert "練習は火曜18時だよ！" in sent_content

    @pytest.mark.asyncio
    async def test_参照元が回答に含まれる(self):
        search_service = AsyncMock()
        search_service.search = AsyncMock(return_value=make_search_results())
        ai_service = AsyncMock()
        ai_service.generate = AsyncMock(return_value=make_answer(
            content="練習は火曜だよ！",
            sources=["部活ルール", "年間スケジュール"],
        ))

        cog = AskCog(MagicMock(), search_service, ai_service)
        interaction = make_interaction()

        await cog.anna.callback(cog, interaction, "練習日は？")

        sent_content = interaction.followup.send.call_args[1].get("content") or interaction.followup.send.call_args[0][0]
        assert "部活ルール" in sent_content

    @pytest.mark.asyncio
    async def test_リクエスト受信時にログが記録される(self, caplog):
        search_service = AsyncMock()
        search_service.search = AsyncMock(return_value=[])
        ai_service = AsyncMock()
        ai_service.generate = AsyncMock(return_value=make_answer(
            content="見当たらなかったよ",
            sources=[],
            has_context=False,
        ))

        cog = AskCog(MagicMock(), search_service, ai_service)
        interaction = make_interaction()

        with caplog.at_level(logging.INFO, logger="bot.cogs.ask"):
            await cog.anna.callback(cog, interaction, "テスト質問")

        log_messages = " ".join(r.message for r in caplog.records)
        assert "12345" in log_messages or "テスト部員" in log_messages

    @pytest.mark.asyncio
    async def test_回答完了時に処理時間がログに記録される(self, caplog):
        search_service = AsyncMock()
        search_service.search = AsyncMock(return_value=make_search_results())
        ai_service = AsyncMock()
        ai_service.generate = AsyncMock(return_value=make_answer())

        cog = AskCog(MagicMock(), search_service, ai_service)
        interaction = make_interaction()

        with caplog.at_level(logging.INFO, logger="bot.cogs.ask"):
            await cog.anna.callback(cog, interaction, "テスト")

        log_messages = " ".join(r.getMessage() for r in caplog.records)
        assert "成功" in log_messages or "完了" in log_messages


class TestFormatResponse:
    """回答フォーマットのテスト"""

    def test_2000文字を超える回答は省略される(self):
        cog = AskCog(MagicMock(), AsyncMock(), AsyncMock())
        long_content = "あ" * 2500
        answer = GeneratedAnswer(content=long_content, sources=[], has_sufficient_context=True)

        result = cog._format_response(answer)
        assert len(result) <= 2000

    def test_参照元なしの場合は本文のみ(self):
        cog = AskCog(MagicMock(), AsyncMock(), AsyncMock())
        answer = GeneratedAnswer(content="回答だよ", sources=[], has_sufficient_context=False)

        result = cog._format_response(answer)
        assert result == "回答だよ"
        assert "参考" not in result

    def test_複数参照元がカンマ区切りで付与される(self):
        cog = AskCog(MagicMock(), AsyncMock(), AsyncMock())
        answer = GeneratedAnswer(content="回答", sources=["資料A", "資料B"], has_sufficient_context=True)

        result = cog._format_response(answer)
        assert "資料A" in result
        assert "資料B" in result


class TestAskCogErrorHandling:
    """エラーハンドリングとユーザー向けメッセージのテスト"""

    @pytest.mark.asyncio
    async def test_検索エラー時にユーザー向けメッセージが返される(self):
        search_service = AsyncMock()
        search_service.search = AsyncMock(
            side_effect=SearchError("検索失敗", status_code=503)
        )
        ai_service = AsyncMock()

        cog = AskCog(MagicMock(), search_service, ai_service)
        interaction = make_interaction()

        await cog.anna.callback(cog, interaction, "テスト質問")

        interaction.followup.send.assert_called_once()
        sent = interaction.followup.send.call_args[1].get("content") or interaction.followup.send.call_args[0][0]
        assert "調べられない" in sent or "回答できません" in sent

    @pytest.mark.asyncio
    async def test_生成エラー時にユーザー向けメッセージが返される(self):
        search_service = AsyncMock()
        search_service.search = AsyncMock(return_value=make_search_results())
        ai_service = AsyncMock()
        ai_service.generate = AsyncMock(
            side_effect=GenerateError("API失敗")
        )

        cog = AskCog(MagicMock(), search_service, ai_service)
        interaction = make_interaction()

        await cog.anna.callback(cog, interaction, "テスト質問")

        interaction.followup.send.assert_called_once()
        sent = interaction.followup.send.call_args[1].get("content") or interaction.followup.send.call_args[0][0]
        assert "失敗" in sent or "うまくいかな" in sent

    @pytest.mark.asyncio
    async def test_予期しないエラー時にユーザー向けメッセージが返される(self):
        search_service = AsyncMock()
        search_service.search = AsyncMock(
            side_effect=RuntimeError("unexpected")
        )
        ai_service = AsyncMock()

        cog = AskCog(MagicMock(), search_service, ai_service)
        interaction = make_interaction()

        await cog.anna.callback(cog, interaction, "テスト質問")

        interaction.followup.send.assert_called_once()
        sent = interaction.followup.send.call_args[1].get("content") or interaction.followup.send.call_args[0][0]
        assert "うまくいかな" in sent or "管理者" in sent

    @pytest.mark.asyncio
    async def test_エラーメッセージに内部詳細が含まれない(self):
        search_service = AsyncMock()
        search_service.search = AsyncMock(
            side_effect=SearchError("https://internal.search.windows.net で失敗", status_code=503)
        )
        ai_service = AsyncMock()

        cog = AskCog(MagicMock(), search_service, ai_service)
        interaction = make_interaction()

        await cog.anna.callback(cog, interaction, "テスト")

        sent = interaction.followup.send.call_args[1].get("content") or interaction.followup.send.call_args[0][0]
        assert "internal.search.windows.net" not in sent
        assert "Traceback" not in sent

    @pytest.mark.asyncio
    async def test_エラー時に開発者向けログが記録される(self, caplog):
        search_service = AsyncMock()
        search_service.search = AsyncMock(
            side_effect=SearchError("接続失敗", status_code=503)
        )
        ai_service = AsyncMock()

        cog = AskCog(MagicMock(), search_service, ai_service)
        interaction = make_interaction()

        with caplog.at_level(logging.ERROR, logger="bot.cogs.ask"):
            await cog.anna.callback(cog, interaction, "テスト")

        assert len(caplog.records) >= 1
        error_log = caplog.records[0].getMessage()
        assert "SearchError" in error_log or "接続失敗" in error_log
