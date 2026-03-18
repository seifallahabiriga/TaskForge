from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.task_repository import TaskRepository
from backend.core.enums import TaskStatus
from backend.services.task_lifecycle_engine import TaskLifecycleEngine
from backend.queue.producer import Producer
from backend.core.exceptions import (
    TaskNotFoundError,
    TaskExecutionError,
    TaskPermissionError
)


class TaskService:

    def __init__(self):
        self.task_repo = TaskRepository()
        self.engine = TaskLifecycleEngine()
        self.producer = Producer()

    # ------------------------------------------------------------------ #
    # Task Creation                                                        #
    # ------------------------------------------------------------------ #

    async def create_task(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        name: str,
        task_type: str,
        input_payload: dict,
        priority: int = 0,
        model_version_id: str | None = None,
    ):
        # Step 1 — Persist task (initial PENDING state)
        task = await self.task_repo.create_task(
            db,
            user_id=user_id,
            name=name,
            task_type=task_type,
            input_payload=input_payload,
            priority=priority,
            model_version_id=model_version_id,
        )

        # Step 2 — Transition to QUEUED (system orchestration state)
        await self.queue_task(db, task_id=task.id)

        # Step 3 — Send job to queue broker
        self.producer.enqueue_task(
            task_id=task.id,
            payload=input_payload,
            priority=priority,
        )

        return task

    # ------------------------------------------------------------------ #
    # Lifecycle Transitions (called internally or by Celery workers)      #
    # ------------------------------------------------------------------ #

    async def queue_task(self, db: AsyncSession, *, task_id: str):
        task = await self._get_or_raise(db, task_id)
        self.engine.validate_transition(task.status, TaskStatus.QUEUED)
        return await self.task_repo.update_task_status(db, task_id, TaskStatus.QUEUED)

    async def start_task_execution(self, db: AsyncSession, *, task_id: str):
        task = await self._get_or_raise(db, task_id)
        self.engine.validate_transition(task.status, TaskStatus.RUNNING)
        return await self.task_repo.update_task_status(db, task_id, TaskStatus.RUNNING)

    async def complete_task_execution(self, db: AsyncSession, *, task_id: str):
        task = await self._get_or_raise(db, task_id)
        self.engine.validate_transition(task.status, TaskStatus.SUCCESS)
        return await self.task_repo.update_task_status(db, task_id, TaskStatus.SUCCESS)

    async def fail_task_execution(
        self, db: AsyncSession, *, task_id: str, error_message: str
    ):
        task = await self._get_or_raise(db, task_id)
        self.engine.validate_transition(task.status, TaskStatus.FAILED)

        task.error_message = error_message
        await db.commit()
        await db.refresh(task)

        return await self.task_repo.update_task_status(db, task_id, TaskStatus.FAILED)

    async def retry_task(self, db: AsyncSession, *, task_id: str):
        task = await self._get_or_raise(db, task_id)

        if task.retry_count >= task.max_retries:
            raise TaskExecutionError(
                f"Task {task_id} has reached max retries ({task.max_retries})"
            )

        self.engine.validate_transition(task.status, TaskStatus.RETRYING)
        await self.task_repo.increment_retry_count(db, task_id)
        return await self.task_repo.update_task_status(db, task_id, TaskStatus.RETRYING)

    # ------------------------------------------------------------------ #
    # Queries                                                             #
    # ------------------------------------------------------------------ #

    async def get_task(self, db: AsyncSession, task_id: str):
        return await self.task_repo.get_task_by_id(db, task_id)

    async def get_user_tasks(self, db: AsyncSession, user_id: str):
        return await self.task_repo.get_tasks_by_user(db, user_id)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    async def _get_or_raise(self, db: AsyncSession, task_id: str):
        task = await self.task_repo.get_task_by_id(db, task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        return task