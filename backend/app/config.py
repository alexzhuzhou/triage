"""
Application configuration using pydantic-settings.

Secrets are fetched in this order:
1. Google Cloud Secret Manager (in production)
2. Environment variables (fallback for local development)
"""
import os
import logging
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load .env file BEFORE anything else
load_dotenv()

logger = logging.getLogger(__name__)


def _get_secret_with_fallback(secret_name: str, env_var_name: str) -> str:
    """
    Get secret from Secret Manager with fallback to environment variable.

    Args:
        secret_name: Name in Secret Manager (e.g., "database-url")
        env_var_name: Environment variable name (e.g., "DATABASE_URL")

    Returns:
        Secret value from Secret Manager or environment variable

    Raises:
        ValueError: If secret not found in either location
    """
    # Try Secret Manager first (only in production)
    if os.getenv("ENV") == "production":
        try:
            from app.utils.secrets import get_secret
            secret_value = get_secret(secret_name)
            if secret_value:
                logger.info(f"✅ Using {env_var_name} from Secret Manager")
                return secret_value
            else:
                logger.warning(f"⚠️  Secret Manager returned None for {secret_name}")
        except Exception as e:
            logger.warning(f"⚠️  Secret Manager failed for {secret_name}: {e}")

    # Fallback to environment variable
    env_value = os.getenv(env_var_name)
    if env_value:
        logger.info(f"✅ Using {env_var_name} from environment variable")
        return env_value

    # Not found in either location
    raise ValueError(
        f"Secret '{secret_name}' not found in Secret Manager and "
        f"environment variable '{env_var_name}' not set"
    )


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database - fetched from Secret Manager in production
    DATABASE_URL: Optional[str] = None

    # OpenAI - fetched from Secret Manager in production
    OPENAI_API_KEY: Optional[str] = None

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

    # CORS Configuration
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"  # Comma-separated list of allowed origins

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    def __init__(self, **kwargs):
        """Initialize settings and fetch secrets from Secret Manager."""
        super().__init__(**kwargs)

        # Fetch sensitive secrets with Secret Manager fallback
        if not self.DATABASE_URL:
            self.DATABASE_URL = _get_secret_with_fallback("database-url", "DATABASE_URL")

        if not self.OPENAI_API_KEY:
            self.OPENAI_API_KEY = _get_secret_with_fallback("openai-api-key", "OPENAI_API_KEY")


# Global settings instance
settings = Settings()
