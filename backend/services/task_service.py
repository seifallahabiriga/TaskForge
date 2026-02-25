from sqlalchemy.orm import Session

from backend.repositories.task_repository import TaskRepository
from backend.core.enums import TaskStatus
from backend.services.task_lifecycle_engine import TaskLifecycleEngine
from backend.core.exceptions import (
    TaskNotFoundError,
    TaskExecutionError,
    TaskPermissionError,
)


class TaskService:

    def __init__(self):
        self.task_repo = TaskRepository()
        self.engine = TaskLifecycleEngine()

    # ------------------------------------------------------------------ #
    # Task Creation                                                        #
    # ------------------------------------------------------------------ #

    def create_task(
        self,
        db: Session,
        *,
        user_id: str,
        name: str,
        task_type: str,
        input_payload: dict,
        priority: int = 0,
        model_version_id: str | None = None,
    ):
        task = self.task_repo.create_task(
            db,
            user_id=user_id,
            name=name,
            task_type=task_type,
            input_payload=input_payload,
            priority=priority,
            model_version_id=model_version_id,
        )

        return task

    # ------------------------------------------------------------------ #
    # Lifecycle Transitions (called internally or by Celery workers)      #
    # ------------------------------------------------------------------ #

    def queue_task(self, db: Session, *, task_id: str):
        task = self._get_or_raise(db, task_id)
        self.engine.validate_transition(task.status, TaskStatus.QUEUED)
        return self.task_repo.update_task_status(db, task_id, TaskStatus.QUEUED)

    def start_task_execution(self, db: Session, *, task_id: str):
        task = self._get_or_raise(db, task_id)
        self.engine.validate_transition(task.status, TaskStatus.RUNNING)
        return self.task_repo.update_task_status(db, task_id, TaskStatus.RUNNING)

    def complete_task_execution(self, db: Session, *, task_id: str):
        task = self._get_or_raise(db, task_id)
        self.engine.validate_transition(task.status, TaskStatus.SUCCESS)
        return self.task_repo.update_task_status(db, task_id, TaskStatus.SUCCESS)

    def fail_task_execution(
        self, db: Session, *, task_id: str, error_message: str
    ):
        task = self._get_or_raise(db, task_id)
        self.engine.validate_transition(task.status, TaskStatus.FAILED)

        task.error_message = error_message
        db.commit()
        db.refresh(task)

        return self.task_repo.update_task_status(db, task_id, TaskStatus.FAILED)

    def retry_task(self, db: Session, *, task_id: str):
        task = self._get_or_raise(db, task_id)

        if task.retry_count >= task.max_retries:
            raise TaskExecutionError(
                f"Task {task_id} has reached max retries ({task.max_retries})"
            )

        self.engine.validate_transition(task.status, TaskStatus.RETRYING)
        self.task_repo.increment_retry_count(db, task_id)
        return self.task_repo.update_task_status(db, task_id, TaskStatus.RETRYING)

    # ------------------------------------------------------------------ #
    # Queries                                                             #
    # ------------------------------------------------------------------ #

    def get_task(self, db: Session, task_id: str):
        return self.task_repo.get_task_by_id(db, task_id)

    def get_user_tasks(self, db: Session, user_id: str):
        return self.task_repo.get_tasks_by_user(db, user_id)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _get_or_raise(self, db: Session, task_id: str):
        task = self.task_repo.get_task_by_id(db, task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        return task