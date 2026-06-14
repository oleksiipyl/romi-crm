from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://postgres:postgres@localhost:5432/romi_crm"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    zapier_webhook_secret: str = ""
    app_env: str = "development"
    kb_path: str = "data/fast_glass_kb.json"
    log_level: str = "INFO"

    @property
    def kb_file_path(self) -> Path:
        """Resolve KB path relative to backend/ root."""
        path = Path(self.kb_path)
        if path.is_absolute():
            return path
        backend_root = Path(__file__).resolve().parent.parent
        return backend_root / path


def get_settings() -> Settings:
    return Settings()
