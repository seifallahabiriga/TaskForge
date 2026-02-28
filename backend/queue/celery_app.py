from celery import Celery
from kombu import Queue
from backend.core.config import settings


# Create Celery application instance
celery_app = Celery(
    "ai_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)


# Core Celery configuration
celery_app.conf.update(

    # Task Routing & Queues
    task_default_queue=settings.CELERY_DEFAULT_QUEUE,
    task_queues=(
        Queue(settings.CELERY_DEFAULT_QUEUE),
        Queue(settings.CELERY_HIGH_PRIORITY_QUEUE),
        Queue(settings.CELERY_LOW_PRIORITY_QUEUE),
    ),

    # Serialization (Security Critical)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],   # Prevents pickle execution (security risk)

    # Reliability & Execution
    task_acks_late=True,              # Acknowledge after execution (prevents task loss)
    worker_prefetch_multiplier=1,     # Prevents worker hoarding tasks
    task_reject_on_worker_lost=True,  # Re-queue if worker crashes

    # Result Expiry
    result_expires=3600,  # 1 hour

    # Timezone
    timezone="UTC",
    enable_utc=True,
)