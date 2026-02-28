from fastapi.concurrency import run_in_threadpool
from backend.queue.celery_app import celery_app
from backend.core.config import settings


class Producer:

    async def enqueue_task(
        self,
        *,
        task_id: str,
        payload: dict,
        priority: int | None = None,
    ):
        """
        Send job to distributed queue using a thread pool
        so it doesn't block the ASGI event loop.
        """

        return await run_in_threadpool(
            celery_app.send_task,
            "app.queue.tasks.execute_ai_task",
            args=[task_id, payload],
            queue=settings.CELERY_DEFAULT_QUEUE,
            priority=priority,
            retry=True,
        )