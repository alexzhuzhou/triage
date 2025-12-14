"""
Application configuration using pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str

    # OpenAI
    OPENAI_API_KEY: str

    # Environment
    ENV: str = "development"

    # Email Integration (Optional)
    EMAIL_ENABLED: bool = False
    EMAIL_IMAP_SERVER: str = "imap.gmail.com"
    EMAIL_ADDRESS: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_PORT: int = 993
    EMAIL_USE_SSL: bool = True
    EMAIL_POLL_INTERVAL: int = 60  # seconds

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Global settings instance
settings = Settings()
