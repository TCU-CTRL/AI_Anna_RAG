import os
from dataclasses import dataclass

DEFAULT_GEMINI_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
)


@dataclass(frozen=True)
class Config:
    # Discord
    discord_token: str

    # Azure AI Search
    search_endpoint: str
    search_api_key: str
    search_index_name: str

    # Google AI Studio (Gemini)
    gemini_api_key: str
    gemini_models: tuple[str, ...] = DEFAULT_GEMINI_MODELS

    @classmethod
    def from_env(cls) -> "Config":
        """環境変数から Config を生成する。必須項目が欠けている場合は ValueError を送出する。"""
        mapping = {
            "discord_token": "DISCORD_TOKEN",
            "search_endpoint": "AZURE_SEARCH_ENDPOINT",
            "search_api_key": "AZURE_SEARCH_API_KEY",
            "search_index_name": "AZURE_SEARCH_INDEX_NAME",
            "gemini_api_key": "GEMINI_API_KEY",
        }

        values: dict[str, str] = {}
        for field_name, env_var in mapping.items():
            value = os.environ.get(env_var)
            if not value:
                raise ValueError(
                    f"必須環境変数 {env_var} が設定されていません"
                )
            values[field_name] = value

        return cls(**values)
