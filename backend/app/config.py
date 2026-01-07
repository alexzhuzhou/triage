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

    # Redis & Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    QUEUE_DEFAULT_TIMEOUT: int = 600  # 10 minutes
    QUEUE_RETRY_ATTEMPTS: int = 5

    # Testing (for simulating failures)
    SIMULATE_LLM_FAILURES: bool = False  # Set to True to test retry logic
    LLM_FAILURE_RATE: float = 0.7  # 0.0-1.0 (70% = fail 70% of the time)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Global settings instance
settings = Settings()
