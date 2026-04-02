import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.config import Config
from bot.services.ai import AIService, GenerateError, GeneratedAnswer
from bot.services.search import SearchResult


def make_config() -> Config:
    return Config(
        discord_token="test",
        search_endpoint="https://test.search.windows.net",
        search_api_key="test-search-key",
        search_index_name="test-index",
        gemini_api_key="test-gemini-key",
        gemini_models=("gemini-2.0-flash",),
    )


def make_search_results() -> list[SearchResult]:
    return [
        SearchResult(
            id="doc-1",
            title="部活ルール",
            content="練習は毎週火曜と木曜の18時から行います。",
            source="docs/rules.md",
            score=2.0,
        ),
        SearchResult(
            id="doc-2",
            title="年間スケジュール",
            content="夏合宿は8月に実施予定です。",
            source="docs/schedule.md",
            score=1.5,
        ),
    ]


def make_mock_response(text: str) -> MagicMock:
    mock_response = MagicMock()
    mock_response.text = text
    return mock_response


def make_service_with_mock(response_text: str = "回答だよ！", side_effect=None):
    """AIService を作成し、Gemini Client をモックする"""
    with patch("bot.services.ai.genai.Client") as mock_client_cls:
        mock_aio_models = AsyncMock()
        if side_effect:
            mock_aio_models.generate_content = AsyncMock(side_effect=side_effect)
        else:
            mock_aio_models.generate_content = AsyncMock(
                return_value=make_mock_response(response_text)
            )
        mock_client = MagicMock()
        mock_client.aio.models = mock_aio_models
        mock_client_cls.return_value = mock_client

        service = AIService(make_config())
        return service, mock_aio_models


class TestAIService:
    """AIService.generate のテスト"""

    @pytest.mark.asyncio
    async def test_検索結果をコンテキストとして回答を生成する(self):
        service, _ = make_service_with_mock("練習は毎週火曜と木曜の18時からだよ！")

        answer = await service.generate("練習日はいつですか", make_search_results())

        assert isinstance(answer, GeneratedAnswer)
        assert "練習" in answer.content
        assert answer.has_sufficient_context is True

    @pytest.mark.asyncio
    async def test_システムプロンプトにキャラクター指示が含まれる(self):
        service, mock_aio = make_service_with_mock("テスト回答だよ！")

        await service.generate("テスト質問", make_search_results())

        call_kwargs = mock_aio.generate_content.call_args[1]
        system_instruction = call_kwargs["config"].system_instruction
        assert "anna" in system_instruction
        assert "親しみやすく" in system_instruction

    @pytest.mark.asyncio
    async def test_システムプロンプトに検索結果が埋め込まれる(self):
        service, mock_aio = make_service_with_mock("回答だよ！")

        await service.generate("練習日", make_search_results())

        call_kwargs = mock_aio.generate_content.call_args[1]
        system_instruction = call_kwargs["config"].system_instruction
        assert "部活ルール" in system_instruction
        assert "毎週火曜と木曜" in system_instruction

    @pytest.mark.asyncio
    async def test_参照元タイトルのリストが返される(self):
        service, _ = make_service_with_mock("回答だよ！")

        answer = await service.generate("練習日", make_search_results())

        assert "部活ルール" in answer.sources
        assert "年間スケジュール" in answer.sources

    @pytest.mark.asyncio
    async def test_検索結果が空の場合にhas_sufficient_contextがFalseになる(self):
        service, _ = make_service_with_mock("部内資料には見当たらなかったよ")

        answer = await service.generate("存在しない情報", [])

        assert answer.has_sufficient_context is False

    @pytest.mark.asyncio
    async def test_質問文がモデルに送信される(self):
        service, mock_aio = make_service_with_mock("回答")

        await service.generate("次の活動日はいつですか", make_search_results())

        call_kwargs = mock_aio.generate_content.call_args[1]
        assert call_kwargs["contents"] == "次の活動日はいつですか"


class TestAIServiceErrorHandling:
    """生成エラーハンドリングのテスト"""

    @pytest.mark.asyncio
    async def test_検索結果が空の場合にプロンプトで正直に伝えるよう指示する(self):
        service, mock_aio = make_service_with_mock("見当たらなかったよ")

        await service.generate("存在しない質問", [])

        call_kwargs = mock_aio.generate_content.call_args[1]
        system_instruction = call_kwargs["config"].system_instruction
        assert "見当たらなかった" in system_instruction or "検索結果なし" in system_instruction

    @pytest.mark.asyncio
    async def test_API呼び出し失敗でGenerateErrorが送出される(self):
        service, _ = make_service_with_mock(side_effect=Exception("API error"))

        with pytest.raises(GenerateError):
            await service.generate("テスト", make_search_results())

    @pytest.mark.asyncio
    async def test_エラー発生時にログが記録される(self, caplog):
        service, _ = make_service_with_mock(side_effect=Exception("Rate limit exceeded"))

        with caplog.at_level(logging.ERROR, logger="bot.services.ai"):
            with pytest.raises(GenerateError):
                await service.generate("テスト", make_search_results())

        assert len(caplog.records) >= 1

    @pytest.mark.asyncio
    async def test_予期しない例外でもGenerateErrorが送出される(self):
        service, _ = make_service_with_mock(side_effect=RuntimeError("unexpected"))

        with pytest.raises(GenerateError):
            await service.generate("テスト", make_search_results())


class TestAIServiceFallback:
    """モデルフォールバックのテスト"""

    @pytest.mark.asyncio
    async def test_レート制限時に次のモデルにフォールバックする(self):
        from google.genai.errors import ClientError

        rate_limit_error = ClientError(429, {"error": {"message": "rate limited"}})

        with patch("bot.services.ai.genai.Client") as mock_client_cls:
            mock_aio_models = AsyncMock()
            # 1回目: 429、2回目: 成功
            mock_aio_models.generate_content = AsyncMock(
                side_effect=[rate_limit_error, make_mock_response("フォールバック成功！")]
            )
            mock_client = MagicMock()
            mock_client.aio.models = mock_aio_models
            mock_client_cls.return_value = mock_client

            config = Config(
                discord_token="test",
                search_endpoint="https://test.search.windows.net",
                search_api_key="test-search-key",
                search_index_name="test-index",
                gemini_api_key="test-gemini-key",
                gemini_models=("gemini-2.0-flash", "gemini-2.0-flash-lite"),
            )
            service = AIService(config)

            answer = await service.generate("テスト", make_search_results())

            assert answer.content == "フォールバック成功！"
            assert mock_aio_models.generate_content.call_count == 2

    @pytest.mark.asyncio
    async def test_全モデルでレート制限の場合にGenerateErrorが送出される(self):
        from google.genai.errors import ClientError

        rate_limit_error = ClientError(429, {"error": {"message": "rate limited"}})

        with patch("bot.services.ai.genai.Client") as mock_client_cls:
            mock_aio_models = AsyncMock()
            mock_aio_models.generate_content = AsyncMock(side_effect=rate_limit_error)
            mock_client = MagicMock()
            mock_client.aio.models = mock_aio_models
            mock_client_cls.return_value = mock_client

            config = Config(
                discord_token="test",
                search_endpoint="https://test.search.windows.net",
                search_api_key="test-search-key",
                search_index_name="test-index",
                gemini_api_key="test-gemini-key",
                gemini_models=("model-a", "model-b"),
            )
            service = AIService(config)

            with pytest.raises(GenerateError, match="全モデルでレート制限"):
                await service.generate("テスト", make_search_results())

            assert mock_aio_models.generate_content.call_count == 2

    @pytest.mark.asyncio
    async def test_レート制限以外のエラーはフォールバックせず即座に送出される(self):
        from google.genai.errors import ClientError

        auth_error = ClientError(403, {"error": {"message": "forbidden"}})

        with patch("bot.services.ai.genai.Client") as mock_client_cls:
            mock_aio_models = AsyncMock()
            mock_aio_models.generate_content = AsyncMock(side_effect=auth_error)
            mock_client = MagicMock()
            mock_client.aio.models = mock_aio_models
            mock_client_cls.return_value = mock_client

            config = Config(
                discord_token="test",
                search_endpoint="https://test.search.windows.net",
                search_api_key="test-search-key",
                search_index_name="test-index",
                gemini_api_key="test-gemini-key",
                gemini_models=("model-a", "model-b"),
            )
            service = AIService(config)

            with pytest.raises(GenerateError):
                await service.generate("テスト", make_search_results())

            # 403 はフォールバックしないので 1 回だけ
            assert mock_aio_models.generate_content.call_count == 1
