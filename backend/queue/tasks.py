from celery import Task
from sqlalchemy.orm import Session
import socket
import time

from backend.queue.celery_app import celery_app
from backend.db.session import SyncSessionLocal
from backend.services.execution_service import ExecutionService
from backend.services.task_service import TaskService
from backend.core.config import settings


class DatabaseTask(Task):

    _db: Session | None = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SyncSessionLocal()
        return self._db

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.queue.tasks.execute_ai_task",
    max_retries=settings.CELERY_MAX_RETRIES,
    default_retry_delay=settings.CELERY_RETRY_DELAY_SECONDS,
)
def execute_ai_task(self, task_id: str, payload: dict):

    execution_service = ExecutionService(self.db)
    task_service = TaskService()

    worker_id = socket.gethostname()

    # Create execution attempt
    execution = execution_service.create_execution(
        task_id=task_id,
        worker_id=worker_id,
    )

    try:
        # Task lifecycle transition
        task_service.start_task_execution(self.db, task_id=task_id)

        # Execution lifecycle transition
        execution_service.mark_execution_running(
            execution_id=execution.id
        )

        start_time = time.time()

        # Core compute
        result = execution_service.run(
            task_id=task_id,
            payload=payload,
        )

        runtime_ms = int((time.time() - start_time) * 1000)

        execution_service.mark_execution_success(
            execution_id=execution.id,
            runtime_ms=runtime_ms,
            metrics={"worker_id": worker_id},
        )

        task_service.complete_task_execution(
            self.db,
            task_id=task_id,
        )

        return result

    except Exception as exc:

        runtime_ms = int((time.time() - start_time) * 1000)

        execution_service.mark_execution_failed(
            execution_id=execution.id,
            error_message=str(exc),
            runtime_ms=runtime_ms,
        )

        try:
            task_service.retry_task(self.db, task_id=task_id)
            raise self.retry(exc=exc)

        except self.MaxRetriesExceededError:
            task_service.fail_task_execution(
                self.db,
                task_id=task_id,
                error_message=str(exc),
            )
            raise