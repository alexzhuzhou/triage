"""
Application configuration using pydantic-settings.
"""
from typing import Optional
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
    EMAIL_POLL_INTERVAL: int = 20  # seconds

    # Redis & Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    QUEUE_DEFAULT_TIMEOUT: int = 600  # 10 minutes
    QUEUE_RETRY_ATTEMPTS: int = 5

    # Testing (for simulating failures)
    SIMULATE_LLM_FAILURES: bool = False  # Set to True to test retry logic
    LLM_FAILURE_RATE: float = 0.7  # 0.0-1.0 (70% = fail 70% of the time)

    # PDF Processing (for vision-based extraction)
    PDF_CONVERSION_ENABLED: bool = True  # Enable PDF-to-image conversion
    PDF_CONVERSION_DPI: int = 150  # Image resolution (150 = balanced, 300 = high quality)
    PDF_MAX_PAGES: Optional[int] = None  # Maximum pages to convert (None = unlimited)
    PDF_IMAGE_FORMAT: str = "png"  # Output format ('png' or 'jpeg')
    PDF_COMPRESSION_QUALITY: int = 85  # JPEG quality 0-100 (only for jpeg format)

    # Vision API Settings
    VISION_IMAGE_DETAIL: str = "high"  # OpenAI vision detail level ('low', 'high', 'auto')

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Global settings instance
settings = Settings()
