import logging
from dataclasses import dataclass

import aiohttp

from bot.config import Config

logger = logging.getLogger(__name__)

API_VERSION = "2024-07-01"


class SearchError(Exception):
    """Azure AI Search の検索処理で発生するエラー"""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class SearchResult:
    id: str
    title: str
    content: str
    source: str
    score: float


class SearchService:
    def __init__(self, config: Config) -> None:
        self._endpoint = config.search_endpoint
        self._api_key = config.search_api_key
        self._index_name = config.search_index_name
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def search(self, query: str, top: int = 5) -> list[SearchResult]:
        """Azure AI Search に対して BM25 検索を実行し、関連ドキュメントを返す。"""
        session = await self._get_session()
        url = (
            f"{self._endpoint}/indexes/{self._index_name}"
            f"/docs/search?api-version={API_VERSION}"
        )
        headers = {
            "Content-Type": "application/json",
            "api-key": self._api_key,
        }
        body = {
            "search": query,
            "top": top,
            "select": "id,title,content,source",
            "queryType": "simple",
        }

        try:
            async with session.post(url, json=body, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(
                "Azure AI Search API エラー: status=%s, endpoint=%s, index=%s",
                e.status,
                self._endpoint,
                self._index_name,
            )
            raise SearchError(
                f"検索 API エラー (HTTP {e.status})",
                status_code=e.status,
            ) from e
        except aiohttp.ClientError as e:
            logger.error(
                "Azure AI Search 接続エラー: endpoint=%s, error=%s",
                self._endpoint,
                str(e),
            )
            raise SearchError(
                f"検索サービスへの接続に失敗しました: {e}",
            ) from e

        results = [
            SearchResult(
                id=doc["id"],
                title=doc.get("title", ""),
                content=doc.get("content", ""),
                source=doc.get("source", ""),
                score=doc.get("@search.score", 0.0),
            )
            for doc in data.get("value", [])
        ]
        results.sort(key=lambda r: r.score, reverse=True)
        return results
