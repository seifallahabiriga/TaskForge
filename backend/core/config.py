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
    CELERY_MAX_RETRIES: int = 3      # Max retry attempts for failed tasks 
    CELERY_RETRY_DELAY_SECONDS: int = 5 # Delay between retries (seconds)

    # Third-party API keys
    OPENROUTER_API_KEY: str          # OpenRouter API key
    HUGGINGFACE_API_KEY: str         # HuggingFace API key
    GROQ_API_KEY: str                # Groq API key
    GEMINI_API_KEY: str              # Google Gemini API key
    APP_URL: str = "http://localhost:8000"   # shown in OpenRouter dashboard
    APP_NAME: str = "TaskForge"

    # Authentication security
    ALGORITHM: str                  # JWT signing algorithm (e.g., HS256)
    SECRET_KEY: str                 # Cryptographic signing secret
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15   # Access token lifetime (minutes)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # Refresh token lifetime (days)

    # API defaults
    API_INFERENCE_TOKEN_LIMIT: int = 1000       # Max tokens per request (default for all providers)
    API_INFERENCE_TEMPERATURE: float = 0.7     # Default temperature for text generation
    API_ANALYSIS_TOKEN_LIMIT: int = 500        # Max tokens per request (default for analysis tasks)
    API_ANALYSIS_TEMPERATURE: float = 0.2     # Default temperature for analysis tasks

    # Rate limiting
    RATE_LIMIT_AUTH_REGISTER: int = 5          # requests per hour per IP
    RATE_LIMIT_AUTH_LOGIN: int = 10            # requests per 15 min per IP
    RATE_LIMIT_TASK_CREATE: int = 30           # requests per hour per user
    RATE_LIMIT_TASK_READ: int = 120            # requests per hour per user
    RATE_LIMIT_DEFAULT: int = 60               # requests per hour per user

    # Runtime environment control
    ENVIRONMENT: str = "development"   # Deployment context (development/staging/production)
    DEBUG: bool = False                # Enables verbose error diagnostics (disable in production)

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"     # Ensures consistent secret parsing
        extra = "forbid"                # Rejects undefined environment variables


settings = Settings()