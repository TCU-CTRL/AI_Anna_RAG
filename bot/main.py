import logging
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from bot.config import Config
from bot.cogs.ask import AskCog
from bot.services.ai import AIService
from bot.services.search import SearchService

logger = logging.getLogger(__name__)


def create_bot(config: Config) -> commands.Bot:
    """Config から Bot インスタンスを作成し、コマンドを登録する。"""
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    search_service = SearchService(config)
    ai_service = AIService(config)
    cog = AskCog(bot, search_service, ai_service)
    bot.tree.add_command(cog.anna)

    @bot.event
    async def on_ready():
        logger.info("Anna Bot が起動しました: %s", bot.user)
        guild_id = os.environ.get("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            logger.info("Guild コマンドを同期しました: %s", guild_id)
        else:
            await bot.tree.sync()
            logger.info("Global コマンドを同期しました")

    return bot


def main() -> None:
    """Bot を起動する。"""
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config = Config.from_env()
    bot = create_bot(config)
    bot.run(config.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
