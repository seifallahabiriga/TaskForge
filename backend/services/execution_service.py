import time
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

    def __init__(self, db: Session):
        self.db = db
        self.execution_repo = ExecutionRepository()
        self.task_repo = TaskRepository()

    # ------------------------------------------------------------------ #
    # Creation                                                            #
    # ------------------------------------------------------------------ #

    def create_execution(
        self,
        *,
        task_id: str,
        worker_id: str,
    ):
        task = self.task_repo.get_task_by_id(self.db, task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")

        return self.execution_repo.create_execution(
            self.db,
            task_id=task_id,
            worker_id=worker_id,
            status=ExecutionStatus.PENDING,
            started_at=None,
            completed_at=None,
        )

    # ------------------------------------------------------------------ #
    # Execution State                                                     #
    # ------------------------------------------------------------------ #

    def mark_execution_running(
        self,
        *,
        execution_id: str,
    ):
        execution = self._get_or_raise(execution_id)

        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(execution)

        return execution

    def mark_execution_success(
        self,
        *,
        execution_id: str,
        runtime_ms: int | None = None,
        metrics: dict | None = None,
    ):
        execution = self._get_or_raise(execution_id)

        execution.status = ExecutionStatus.SUCCESS
        execution.completed_at = datetime.utcnow()
        execution.runtime_ms = runtime_ms
        execution.metrics = metrics

        self.db.commit()
        self.db.refresh(execution)

        return execution

    def mark_execution_failed(
        self,
        *,
        execution_id: str,
        error_message: str,
        runtime_ms: int | None = None,
    ):
        execution = self._get_or_raise(execution_id)

        execution.status = ExecutionStatus.FAILED
        execution.completed_at = datetime.utcnow()
        execution.runtime_ms = runtime_ms
        execution.error_message = error_message

        self.db.commit()
        self.db.refresh(execution)

        return execution

    # ------------------------------------------------------------------ #
    # Core Compute                                                        #
    # ------------------------------------------------------------------ #

    def run(
        self,
        *,
        task_id: str,
        payload: dict,
    ):
        task = self.task_repo.get_task_by_id(self.db, task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")

        # Placeholder AI execution logic
        # Replace with model_service routing later

        if task.task_type == "echo":
            return {"output": payload}

        elif task.task_type == "sum":
            numbers = payload.get("numbers", [])
            return {"output": sum(numbers)}

        else:
            raise ValueError(f"Unsupported task type: {task.task_type}")

    # ------------------------------------------------------------------ #
    # Queries                                                             #
    # ------------------------------------------------------------------ #

    def get_execution(self, execution_id: str):
        return self.execution_repo.get_execution_by_id(
            self.db,
            execution_id,
        )

    def get_task_executions(self, task_id: str):
        return self.execution_repo.get_executions_by_task(
            self.db,
            task_id,
        )

    # ------------------------------------------------------------------ #
    # Internal                                                            #
    # ------------------------------------------------------------------ #

    def _get_or_raise(self, execution_id: str):
        execution = self.execution_repo.get_execution_by_id(
            self.db,
            execution_id,
        )
        if not execution:
            raise ExecutionNotFoundError(
                f"Execution {execution_id} not found"
            )
        return execution