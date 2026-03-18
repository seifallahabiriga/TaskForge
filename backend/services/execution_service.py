import time
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.execution_repository import ExecutionRepository
from backend.repositories.task_repository import TaskRepository
from backend.workers.worker_app.job_runner import JobRunner
from backend.core.enums import ExecutionStatus
from backend.core.exceptions import (
    ExecutionNotFoundError,
    TaskNotFoundError,
    TaskExecutionError
)



class ExecutionService:

    def __init__(self):
        self.execution_repo = ExecutionRepository()
        self.task_repo = TaskRepository()

    # ------------------------------------------------------------------ #
    # Creation                                                            #
    # ------------------------------------------------------------------ #

    async def create_execution(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        worker_id: str,
    ):
        task = await self.task_repo.get_task_by_id(db, task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")

        return await self.execution_repo.create_execution(
            db,
            task_id=task_id,
            worker_id=worker_id,
            status=ExecutionStatus.PENDING,
            started_at=None,
            completed_at=None,
        )

    # ------------------------------------------------------------------ #
    # Execution State                                                     #
    # ------------------------------------------------------------------ #

    async def mark_execution_running(
        self,
        db: AsyncSession,
        *,
        execution_id: str,
    ):
        execution = await self._get_or_raise(db, execution_id)

        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.utcnow()

        await db.commit()
        await db.refresh(execution)

        return execution

    async def mark_execution_success(
        self,
        db: AsyncSession,
        *,
        execution_id: str,
        runtime_ms: int | None = None,
        metrics: dict | None = None,
    ):
        execution = await self._get_or_raise(db, execution_id)

        execution.status = ExecutionStatus.SUCCESS
        execution.completed_at = datetime.utcnow()
        execution.runtime_ms = runtime_ms
        execution.metrics = metrics

        await db.commit()
        await db.refresh(execution)

        return execution

    async def mark_execution_failed(
        self,
        db: AsyncSession,
        *,
        execution_id: str,
        error_message: str,
        runtime_ms: int | None = None,
    ):
        execution = await self._get_or_raise(db, execution_id)

        execution.status = ExecutionStatus.FAILED
        execution.completed_at = datetime.utcnow()
        execution.runtime_ms = runtime_ms
        execution.error_message = error_message

        await db.commit()
        await db.refresh(execution)

        return execution

    # ------------------------------------------------------------------ #
    # Core Compute                                                        #
    # ------------------------------------------------------------------ #

    async def run(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        payload: dict,
    ):
        task = await self.task_repo.get_task_by_id(db, task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")

        try:
            # enforce source of truth for task_type
            payload["task_type"] = task.task_type

            return JobRunner.execute(
                task_id=task_id,
                payload=payload,
            )

        except Exception as e:
            raise TaskExecutionError(f"Execution failed: {str(e)}")

    # ------------------------------------------------------------------ #
    # Queries                                                             #
    # ------------------------------------------------------------------ #

    async def get_execution(self, db: AsyncSession, execution_id: str):
        return await self.execution_repo.get_execution_by_id(
            db,
            execution_id,
        )

    async def get_task_executions(self, db: AsyncSession, task_id: str):
        return await self.execution_repo.get_executions_by_task(
            db,
            task_id,
        )

    # ------------------------------------------------------------------ #
    # Internal                                                            #
    # ------------------------------------------------------------------ #

    async def _get_or_raise(self, db: AsyncSession, execution_id: str):
        execution = await self.execution_repo.get_execution_by_id(
            db,
            execution_id,
        )
        if not execution:
            raise ExecutionNotFoundError(
                f"Execution {execution_id} not found"
            )
        return execution