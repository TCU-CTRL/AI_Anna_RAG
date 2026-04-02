import logging
import time
from dataclasses import dataclass

from google import genai
from google.genai.errors import ClientError

from bot.config import Config
from bot.services.search import SearchResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """\
あなたは「anna」という部活のマスコットキャラクターです。

## 口調
- 親しみやすく、丁寧で、軽くかわいげのある口調で話してください
- 「〜だよ」「〜かな」「〜してね」のような柔らかい語尾を使ってください
- 敬語と親しみやすさのバランスを保ってください

## 回答ルール
- 以下の「検索結果」に含まれる情報のみに基づいて回答してください
- 検索結果に含まれない情報については、推測せず「部内資料には見当たらなかったよ」と正直に伝えてください
- 回答の根拠となる資料がある場合は、参照元のタイトルを「参考: 〇〇」の形式で末尾に付けてください
- 情報の正確性を最優先してください

## 検索結果
{search_context}\
"""


class GenerateError(Exception):
    """LLM の回答生成で発生するエラー"""
    pass


@dataclass
class GeneratedAnswer:
    content: str
    sources: list[str]
    has_sufficient_context: bool


class AIService:
    def __init__(self, config: Config) -> None:
        self._client = genai.Client(api_key=config.gemini_api_key)
        self._models = config.gemini_models

    async def generate(
        self,
        question: str,
        search_results: list[SearchResult],
    ) -> GeneratedAnswer:
        """検索結果をコンテキストとして LLM に渡し、anna としての回答を生成する。"""
        has_context = len(search_results) > 0
        search_context = self._format_context(search_results)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(search_context=search_context)

        last_error: Exception | None = None
        for model_name in self._models:
            start_time = time.monotonic()
            try:
                response = await self._client.aio.models.generate_content(
                    model=model_name,
                    contents=question,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.3,
                        max_output_tokens=800,
                    ),
                )
                elapsed = time.monotonic() - start_time
                logger.info("回答生成成功: model=%s, 処理時間=%.2fs", model_name, elapsed)

                content = response.text or ""
                sources = [r.title for r in search_results if r.title]

                return GeneratedAnswer(
                    content=content,
                    sources=sources,
                    has_sufficient_context=has_context,
                )

            except ClientError as e:
                elapsed = time.monotonic() - start_time
                if e.code == 429:
                    logger.warning(
                        "レート制限: model=%s, 処理時間=%.2fs, 次のモデルを試行",
                        model_name,
                        elapsed,
                    )
                    last_error = e
                    continue
                logger.error(
                    "Gemini API エラー: model=%s, %s, 処理時間=%.2fs",
                    model_name,
                    str(e),
                    elapsed,
                )
                raise GenerateError(f"回答生成 API エラー: {e}") from e

            except Exception as e:
                elapsed = time.monotonic() - start_time
                logger.error(
                    "Gemini API エラー: model=%s, %s, 処理時間=%.2fs",
                    model_name,
                    str(e),
                    elapsed,
                )
                raise GenerateError(f"回答生成 API エラー: {e}") from e

        raise GenerateError(
            f"全モデルでレート制限に達しました: {', '.join(self._models)}"
        ) from last_error

    def _format_context(self, results: list[SearchResult]) -> str:
        if not results:
            return "（検索結果なし）"

        parts = []
        for r in results:
            parts.append(f"### {r.title}\n出典: {r.source}\n{r.content}")
        return "\n\n".join(parts)
