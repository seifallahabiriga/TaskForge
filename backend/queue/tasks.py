from celery import Task
from sqlalchemy.orm import Session

from backend.queue.celery_app import celery_app
from backend.db.session import SyncSessionLocal
from backend.services.execution_service import ExecutionService
from backend.core.enums import TaskStatus


class DatabaseTask(Task):
    """
    Custom Celery Task base class that provides
    a database session per task execution.
    """

    _db: Session | None = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SyncSessionLocal()
        return self._db

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """
        Ensures DB session is always closed
        after task finishes (success or failure).
        """
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.queue.tasks.execute_ai_task",
    max_retries=3,
    default_retry_delay=5,
)
def execute_ai_task(self, task_id: str, payload: dict):
    """
    Main distributed execution entrypoint.

    Parameters:
    - task_id: Platform task identifier
    - payload: Serialized job input data
    """

    execution_service = ExecutionService(self.db)

    try:
        # Mark task as running
        execution_service.update_status(task_id, TaskStatus.RUNNING)

        # Execute core AI workflow
        result = execution_service.run(task_id=task_id, payload=payload)

        # Mark success
        execution_service.update_status(task_id, TaskStatus.SUCCESS)

        return result

    except Exception as exc:
        # Increment retry attempt in DB
        execution_service.increment_retry(task_id)

        try:
            # Controlled retry
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            # Final failure state
            execution_service.update_status(
                task_id,
                TaskStatus.FAILED,
                error_message=str(exc),
            )
            raise