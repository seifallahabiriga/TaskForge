from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.db.session import get_async_db
from backend.queue.redis_client import get_redis

router = APIRouter(prefix="/health", tags=["Monitoring"])


# ------------------------------------------------------------------ #
# Deep Health Check                                                    #
# ------------------------------------------------------------------ #

@router.get("/")
async def health_check(
    db: AsyncSession = Depends(get_async_db),
):
    health = {
        "status": "ok",
        "database": "ok",
        "redis": "ok",
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        health["database"] = f"error: {str(e)}"
        health["status"] = "degraded"

    # Check Redis
    try:
        redis = get_redis()
        await redis.ping()
    except Exception as e:
        health["redis"] = f"error: {str(e)}"
        health["status"] = "degraded"

    return health