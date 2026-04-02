import os

import pytest

from bot.config import Config, DEFAULT_GEMINI_MODELS


class TestConfigFromEnv:
    """Config.from_env のテスト"""

    REQUIRED_VARS = {
        "DISCORD_TOKEN": "test-discord-token",
        "AZURE_SEARCH_ENDPOINT": "https://test.search.windows.net",
        "AZURE_SEARCH_API_KEY": "test-search-key",
        "AZURE_SEARCH_INDEX_NAME": "test-index",
        "GEMINI_API_KEY": "test-gemini-key",
    }

    def test_全ての環境変数が設定されている場合にConfigが生成される(self, monkeypatch):
        for key, value in self.REQUIRED_VARS.items():
            monkeypatch.setenv(key, value)

        config = Config.from_env()

        assert config.discord_token == "test-discord-token"
        assert config.search_endpoint == "https://test.search.windows.net"
        assert config.search_api_key == "test-search-key"
        assert config.search_index_name == "test-index"
        assert config.gemini_api_key == "test-gemini-key"
        assert config.gemini_models == DEFAULT_GEMINI_MODELS

    @pytest.mark.parametrize("missing_var", [
        "DISCORD_TOKEN",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_API_KEY",
        "AZURE_SEARCH_INDEX_NAME",
        "GEMINI_API_KEY",
    ])
    def test_必須環境変数が欠けている場合にValueErrorが送出される(self, monkeypatch, missing_var):
        for key, value in self.REQUIRED_VARS.items():
            if key != missing_var:
                monkeypatch.setenv(key, value)
            else:
                monkeypatch.delenv(key, raising=False)

        with pytest.raises(ValueError, match=missing_var):
            Config.from_env()

    def test_Configは読み取り専用である(self, monkeypatch):
        for key, value in self.REQUIRED_VARS.items():
            monkeypatch.setenv(key, value)

        config = Config.from_env()

        with pytest.raises(AttributeError):
            config.discord_token = "new-value"

    def test_デフォルトモデルリストに複数モデルが含まれる(self):
        assert len(DEFAULT_GEMINI_MODELS) >= 2
        assert "gemini-2.5-flash" in DEFAULT_GEMINI_MODELS
