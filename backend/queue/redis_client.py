from redis.asyncio import Redis
from backend.core.config import settings

# Global Redis connection pool (async)
redis_client: Redis | None = None


async def init_redis() -> None:
    """
    Initialize Redis connection pool.
    Called during FastAPI startup.
    """
    global redis_client

    redis_client = Redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,  # Return strings instead of bytes
    )


async def close_redis() -> None:
    """
    Gracefully close Redis connections.
    Called during FastAPI shutdown.
    """
    global redis_client

    if redis_client:
        await redis_client.close()
        redis_client = None


def get_redis() -> Redis:
    """
    Accessor used inside services or dependencies.
    """
    if redis_client is None:
        raise RuntimeError("Redis client not initialized.")
    return redis_client