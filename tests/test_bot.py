from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from bot.config import Config


def make_config() -> Config:
    return Config(
        discord_token="test-token",
        search_endpoint="https://test.search.windows.net",
        search_api_key="test-search-key",
        search_index_name="test-index",
        gemini_api_key="test-gemini-key",
        gemini_models=("gemini-2.0-flash",),
    )


class TestAnnaBot:
    """Anna Bot の起動とコマンド登録のテスト"""

    def test_Botインスタンスが作成できる(self):
        from bot.main import create_bot

        config = make_config()
        bot = create_bot(config)

        assert bot is not None
        assert isinstance(bot, discord.ext.commands.Bot)

    def test_annaコマンドが登録される(self):
        from bot.main import create_bot

        config = make_config()
        bot = create_bot(config)

        command_names = [cmd.name for cmd in bot.tree.get_commands()]
        assert "anna" in command_names

    def test_annaコマンドにquestionパラメータがある(self):
        from bot.main import create_bot

        config = make_config()
        bot = create_bot(config)

        anna_cmd = None
        for cmd in bot.tree.get_commands():
            if cmd.name == "anna":
                anna_cmd = cmd
                break

        assert anna_cmd is not None
        param_names = [p.name for p in anna_cmd.parameters]
        assert "question" in param_names

    def test_Config読み込み失敗で起動しない(self, monkeypatch):
        from bot.main import create_bot

        monkeypatch.delenv("DISCORD_TOKEN", raising=False)

        with pytest.raises(ValueError):
            Config.from_env()

    def test_questionパラメータが必須である(self):
        """discord.py の必須パラメータにより空入力は Discord 側で防止される（Req 1.4）"""
        from bot.main import create_bot

        config = make_config()
        bot = create_bot(config)

        anna_cmd = None
        for cmd in bot.tree.get_commands():
            if cmd.name == "anna":
                anna_cmd = cmd
                break

        question_param = None
        for p in anna_cmd.parameters:
            if p.name == "question":
                question_param = p
                break

        assert question_param is not None
        assert question_param.required is True
