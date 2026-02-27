from datetime import datetime
from sqlalchemy.orm import Session

from backend.repositories.execution_repository import ExecutionRepository
from backend.repositories.task_repository import TaskRepository
from backend.core.enums import ExecutionStatus
from backend.core.exceptions import (
    ExecutionNotFoundError,
    TaskNotFoundError,
)


class ExecutionService:

    def __init__(self):
        self.execution_repo = ExecutionRepository()
        self.task_repo = TaskRepository()

    # ------------------------------------------------------------------ #
    # Creation                                                            #
    # ------------------------------------------------------------------ #

    def create_execution(
        self,
        db: Session,
        *,
        task_id: str,
        worker_id: str,
    ):
        task = self.task_repo.get_task_by_id(db, task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")

        execution = self.execution_repo.create_execution(
            db,
            task_id=task_id,
            worker_id=worker_id,
            status=ExecutionStatus.PENDING,
            started_at=None,
            completed_at=None,
        )

        return execution

    # ------------------------------------------------------------------ #
    # State Transitions                                                   #
    # ------------------------------------------------------------------ #

    def mark_execution_running(
        self,
        db: Session,
        *,
        execution_id: str,
    ):
        execution = self._get_or_raise(db, execution_id)

        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.utcnow()

        db.commit()
        db.refresh(execution)

        return execution

    def mark_execution_success(
        self,
        db: Session,
        *,
        execution_id: str,
        runtime_ms: int | None = None,
        metrics: dict | None = None,
    ):
        execution = self._get_or_raise(db, execution_id)

        execution.status = ExecutionStatus.SUCCESS
        execution.completed_at = datetime.utcnow()
        execution.runtime_ms = runtime_ms
        execution.metrics = metrics

        db.commit()
        db.refresh(execution)

        return execution

    def mark_execution_failed(
        self,
        db: Session,
        *,
        execution_id: str,
        error_message: str,
        runtime_ms: int | None = None,
    ):
        execution = self._get_or_raise(db, execution_id)

        execution.status = ExecutionStatus.FAILED
        execution.completed_at = datetime.utcnow()
        execution.runtime_ms = runtime_ms
        execution.error_message = error_message

        db.commit()
        db.refresh(execution)

        return execution

    # ------------------------------------------------------------------ #
    # Queries                                                             #
    # ------------------------------------------------------------------ #

    def get_execution(self, db: Session, execution_id: str):
        return self.execution_repo.get_execution_by_id(db, execution_id)

    def get_task_executions(self, db: Session, task_id: str):
        return self.execution_repo.get_executions_by_task(db, task_id)

    # ------------------------------------------------------------------ #
    # Internal                                                            #
    # ------------------------------------------------------------------ #

    def _get_or_raise(self, db: Session, execution_id: str):
        execution = self.execution_repo.get_execution_by_id(db, execution_id)
        if not execution:
            raise ExecutionNotFoundError(
                f"Execution {execution_id} not found"
            )
        return execution