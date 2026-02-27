from pydantic_settings import BaseSettings
from pathlib import Path

# Root project directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Database connections
    DATABASE_ASYNC_URL: str   # Async SQLAlchemy connection string (FastAPI layer)
    DATABASE_SYNC_URL: str    # Sync connection string (Celery worker layer)

    # Redis + Celery Infrastructure
    REDIS_URL: str                 # Base Redis instance (caching, rate limiting, pub/sub)
    CELERY_BROKER_URL: str         # Message broker for task distribution
    CELERY_RESULT_BACKEND: str     # Storage backend for task results

    # Queue configuration
    CELERY_DEFAULT_QUEUE: str        # Standard inference jobs
    CELERY_HIGH_PRIORITY_QUEUE: str  # Latency-sensitive jobs
    CELERY_LOW_PRIORITY_QUEUE: str   # Heavy background or batch jobs

    # Authentication security
    ALGORITHM: str                  # JWT signing algorithm (e.g., HS256)
    SECRET_KEY: str                 # Cryptographic signing secret
    ACCESS_TOKEN_EXPIRE_MINUTES: int   # Access token lifetime (minutes)
    REFRESH_TOKEN_EXPIRE_DAYS: int     # Refresh token lifetime (days)

    # Runtime environment control
    ENVIRONMENT: str = "development"   # Deployment context (development/staging/production)
    DEBUG: bool = False                # Enables verbose error diagnostics (disable in production)

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"     # Ensures consistent secret parsing
        extra = "forbid"                # Rejects undefined environment variables


settings = Settings()