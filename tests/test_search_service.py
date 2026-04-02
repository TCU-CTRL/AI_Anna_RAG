import logging
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from bot.config import Config
from bot.services.search import SearchError, SearchResult, SearchService


def make_config() -> Config:
    return Config(
        discord_token="test",
        search_endpoint="https://test.search.windows.net",
        search_api_key="test-search-key",
        search_index_name="test-index",
        gemini_api_key="test-gemini-key",
        gemini_models=("gemini-2.0-flash",),
    )


def make_search_response(docs: list[dict]) -> dict:
    return {"value": docs}


def make_doc(
    doc_id: str = "doc-1",
    title: str = "テスト資料",
    content: str = "テスト本文",
    source: str = "docs/test.md",
    score: float = 1.5,
) -> dict:
    return {
        "id": doc_id,
        "title": title,
        "content": content,
        "source": source,
        "@search.score": score,
    }


class MockResponse:
    """aiohttp のレスポンスを模倣する async context manager"""

    def __init__(self, data: dict, status: int = 200):
        self._data = data
        self.status = status

    async def json(self):
        return self._data

    def raise_for_status(self):
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=self.status,
                message=f"HTTP {self.status}",
            )


class MockContextManager:
    """async with 用のモック"""

    def __init__(self, response: MockResponse):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *args):
        return False


def make_mock_session(response_data: dict, status: int = 200):
    mock_session = MagicMock()
    response = MockResponse(response_data, status)
    mock_session.post = MagicMock(return_value=MockContextManager(response))
    return mock_session


class TestSearchService:
    """SearchService.search のテスト"""

    @pytest.mark.asyncio
    async def test_検索結果をSearchResultリストに変換する(self):
        config = make_config()
        service = SearchService(config)
        response_body = make_search_response([
            make_doc("doc-1", "資料A", "本文A", "docs/a.md", 2.0),
            make_doc("doc-2", "資料B", "本文B", "docs/b.md", 1.5),
        ])

        service._session = make_mock_session(response_body)
        results = await service.search("テスト質問")

        assert len(results) == 2
        assert results[0].id == "doc-1"
        assert results[0].title == "資料A"
        assert results[0].content == "本文A"
        assert results[0].source == "docs/a.md"
        assert results[0].score == 2.0
        assert results[1].id == "doc-2"
        assert results[1].score == 1.5

    @pytest.mark.asyncio
    async def test_検索クエリとtopパラメータが正しくAPIに送信される(self):
        config = make_config()
        service = SearchService(config)
        service._session = make_mock_session(make_search_response([]))

        await service.search("活動日程", top=3)

        call_kwargs = service._session.post.call_args
        url = call_kwargs[0][0]
        request_body = call_kwargs[1]["json"]
        assert "test-index" in url
        assert request_body["search"] == "活動日程"
        assert request_body["top"] == 3

    @pytest.mark.asyncio
    async def test_APIキーがヘッダーに設定される(self):
        config = make_config()
        service = SearchService(config)
        service._session = make_mock_session(make_search_response([]))

        await service.search("テスト")

        call_kwargs = service._session.post.call_args
        headers = call_kwargs[1]["headers"]
        assert headers["api-key"] == "test-search-key"

    @pytest.mark.asyncio
    async def test_結果はスコア降順でソートされる(self):
        config = make_config()
        service = SearchService(config)
        response_body = make_search_response([
            make_doc("doc-1", score=1.0),
            make_doc("doc-2", score=3.0),
            make_doc("doc-3", score=2.0),
        ])
        service._session = make_mock_session(response_body)

        results = await service.search("テスト")

        assert results[0].score == 3.0
        assert results[1].score == 2.0
        assert results[2].score == 1.0


class TestSearchServiceErrorHandling:
    """検索結果なしとエラーハンドリングのテスト"""

    @pytest.mark.asyncio
    async def test_検索結果が0件の場合に空リストを返す(self):
        config = make_config()
        service = SearchService(config)
        service._session = make_mock_session(make_search_response([]))

        results = await service.search("存在しない情報")

        assert results == []

    @pytest.mark.asyncio
    async def test_HTTP401エラーでSearchErrorが送出される(self):
        config = make_config()
        service = SearchService(config)
        service._session = make_mock_session({}, status=401)

        with pytest.raises(SearchError) as exc_info:
            await service.search("テスト")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_HTTP503エラーでSearchErrorが送出される(self):
        config = make_config()
        service = SearchService(config)
        service._session = make_mock_session({}, status=503)

        with pytest.raises(SearchError) as exc_info:
            await service.search("テスト")

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_接続エラーでSearchErrorが送出される(self):
        config = make_config()
        service = SearchService(config)

        mock_session = MagicMock()
        mock_session.post = MagicMock(
            side_effect=aiohttp.ClientError("Connection refused")
        )
        service._session = mock_session

        with pytest.raises(SearchError):
            await service.search("テスト")

    @pytest.mark.asyncio
    async def test_エラー発生時にログが記録される(self, caplog):
        config = make_config()
        service = SearchService(config)
        service._session = make_mock_session({}, status=503)

        with caplog.at_level(logging.ERROR, logger="bot.services.search"):
            with pytest.raises(SearchError):
                await service.search("テスト")

        assert len(caplog.records) >= 1
        log_message = caplog.records[0].message
        assert "503" in log_message

    @pytest.mark.asyncio
    async def test_ログにAPIキーが含まれない(self, caplog):
        config = make_config()
        service = SearchService(config)
        service._session = make_mock_session({}, status=401)

        with caplog.at_level(logging.ERROR, logger="bot.services.search"):
            with pytest.raises(SearchError):
                await service.search("テスト")

        for record in caplog.records:
            assert "test-search-key" not in record.message
