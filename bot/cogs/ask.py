import logging
import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.ai import AIService, GenerateError, GeneratedAnswer
from bot.services.search import SearchError, SearchService

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 2000

ERROR_MSG_SEARCH = "ごめんなさい、今ちょっと調べられないみたい...。少し待ってからもう一度聞いてね！"
ERROR_MSG_GENERATE = "うーん、回答をまとめるのに失敗しちゃった...。もう一度試してみてね！"
ERROR_MSG_UNEXPECTED = "ごめんなさい、何かうまくいかなかったみたい...。管理者に連絡してくれると助かるな"


class AskCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        search_service: SearchService,
        ai_service: AIService,
    ) -> None:
        self.bot = bot
        self._search_service = search_service
        self._ai_service = ai_service

    @app_commands.command(name="anna", description="anna に質問する")
    @app_commands.describe(question="質問内容")
    async def anna(self, interaction: discord.Interaction, question: str) -> None:
        """anna に質問するスラッシュコマンド。"""
        await interaction.response.defer(thinking=True)
        start_time = time.monotonic()

        logger.info(
            "質問を受信: user=%s, user_id=%s",
            interaction.user.display_name,
            interaction.user.id,
        )

        try:
            search_results = await self._search_service.search(question)
            answer = await self._ai_service.generate(question, search_results)
            response_text = self._format_response(answer)
            await interaction.followup.send(content=response_text)

            elapsed = time.monotonic() - start_time
            logger.info(
                "回答完了(成功): user_id=%s, 処理時間=%.2fs",
                interaction.user.id,
                elapsed,
            )

        except SearchError as e:
            elapsed = time.monotonic() - start_time
            logger.error(
                "SearchError: %s, user_id=%s, 処理時間=%.2fs",
                str(e),
                interaction.user.id,
                elapsed,
            )
            await interaction.followup.send(content=ERROR_MSG_SEARCH)

        except GenerateError as e:
            elapsed = time.monotonic() - start_time
            logger.error(
                "GenerateError: %s, user_id=%s, 処理時間=%.2fs",
                str(e),
                interaction.user.id,
                elapsed,
            )
            await interaction.followup.send(content=ERROR_MSG_GENERATE)

        except Exception as e:
            elapsed = time.monotonic() - start_time
            logger.error(
                "予期しないエラー: %s: %s, user_id=%s, 処理時間=%.2fs",
                type(e).__name__,
                str(e),
                interaction.user.id,
                elapsed,
                exc_info=True,
            )
            await interaction.followup.send(content=ERROR_MSG_UNEXPECTED)

    def _format_response(self, answer: GeneratedAnswer) -> str:
        """回答テキストをフォーマットする。参照元があれば付与する。"""
        text = answer.content

        if answer.sources:
            sources_text = "、".join(answer.sources)
            text += f"\n\n📚 参考: {sources_text}"

        if len(text) > MAX_CONTENT_LENGTH:
            text = text[: MAX_CONTENT_LENGTH - 3] + "..."

        return text
