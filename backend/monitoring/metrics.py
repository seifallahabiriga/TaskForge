from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.db.session import get_async_db
from backend.queue.redis_client import get_redis
from backend.core.config import settings
from backend.core.enums import TaskStatus, ExecutionStatus
from backend.models.task import Task
from backend.models.execution import Execution

router = APIRouter(prefix="/metrics", tags=["Monitoring"])


# ------------------------------------------------------------------ #
# Prometheus-style Metrics                                             #
# ------------------------------------------------------------------ #

@router.get("/")
async def get_metrics(
    db: AsyncSession = Depends(get_async_db),
):
    metrics = {}

    # ------------------------------------------------------------------ #
    # Task Status Counts                                                   #
    # ------------------------------------------------------------------ #
    try:
        for task_status in TaskStatus:
            result = await db.execute(
                select(func.count(Task.id)).where(Task.status == task_status)
            )
            metrics[f"tasks_{task_status.value.lower()}"] = result.scalar()
    except Exception as e:
        metrics["tasks_error"] = str(e)

    # ------------------------------------------------------------------ #
    # Execution Status Counts                                              #
    # ------------------------------------------------------------------ #
    try:
        for exec_status in ExecutionStatus:
            result = await db.execute(
                select(func.count(Execution.id)).where(Execution.status == exec_status)
            )
            metrics[f"executions_{exec_status.value.lower()}"] = result.scalar()
    except Exception as e:
        metrics["executions_error"] = str(e)

    # ------------------------------------------------------------------ #
    # Execution Latency (avg runtime_ms)                                   #
    # ------------------------------------------------------------------ #
    try:
        result = await db.execute(
            select(func.avg(Execution.runtime_ms)).where(
                Execution.status == ExecutionStatus.COMPLETED
            )
        )
        avg_runtime = result.scalar()
        metrics["avg_runtime_ms"] = round(avg_runtime, 2) if avg_runtime else 0
    except Exception as e:
        metrics["avg_runtime_ms_error"] = str(e)

    # ------------------------------------------------------------------ #
    # Queue Depth (Redis)                                                  #
    # ------------------------------------------------------------------ #
    try:
        redis = get_redis()
        metrics["queue_depth"] = {
            settings.CELERY_DEFAULT_QUEUE: await redis.llen(settings.CELERY_DEFAULT_QUEUE),
            settings.CELERY_HIGH_PRIORITY_QUEUE: await redis.llen(settings.CELERY_HIGH_PRIORITY_QUEUE),
            settings.CELERY_LOW_PRIORITY_QUEUE: await redis.llen(settings.CELERY_LOW_PRIORITY_QUEUE),
        }
    except Exception as e:
        metrics["queue_depth_error"] = str(e)

    return metrics