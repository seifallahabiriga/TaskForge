from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.execution import Execution
from backend.core.enums import ExecutionStatus


class ExecutionRepository:

    # ------------------------------------------------------------------ #
    # Creation                                                            #
    # ------------------------------------------------------------------ #

    async def create_execution(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        worker_id: str,
        status: ExecutionStatus = ExecutionStatus.PENDING,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> Execution:

        execution = Execution(
            task_id=task_id,
            worker_id=worker_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
        )

        db.add(execution)
        await db.commit()
        await db.refresh(execution)

        return execution

    # ------------------------------------------------------------------ #
    # Queries                                                             #
    # ------------------------------------------------------------------ #

    async def get_execution_by_id(
        self,
        db: AsyncSession,
        execution_id: str,
    ) -> Execution | None:
        result = await db.execute(select(Execution).where(Execution.id == execution_id))
        return result.scalars().first()

    async def get_executions_by_task(
        self,
        db: AsyncSession,
        task_id: str,
        skip: int = 0,
        limit: int = 100,
    ):
        result = await db.execute(
            select(Execution)
            .where(Execution.task_id == task_id)
            .order_by(Execution.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_worker_executions(
        self,
        db: AsyncSession,
        worker_id: str,
        skip: int = 0,
        limit: int = 100,
    ):
        result = await db.execute(
            select(Execution)
            .where(Execution.worker_id == worker_id)
            .order_by(Execution.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def list_executions_by_status(
        self,
        db: AsyncSession,
        status: ExecutionStatus,
        skip: int = 0,
        limit: int = 100,
    ):
        result = await db.execute(
            select(Execution)
            .where(Execution.status == status)
            .order_by(Execution.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    # ------------------------------------------------------------------ #
    # State Updates                                                        #
    # ------------------------------------------------------------------ #

    async def update_execution_status(
        self,
        db: AsyncSession,
        execution_id: str,
        status: ExecutionStatus,
    ) -> Execution | None:

        execution = await self.get_execution_by_id(db, execution_id)
        if not execution:
            return None

        execution.status = status

        if status == ExecutionStatus.RUNNING and execution.started_at is None:
            execution.started_at = datetime.utcnow()

        if status in (ExecutionStatus.SUCCESS, ExecutionStatus.FAILED):
            execution.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(execution)

        return execution

    async def update_execution_metrics(
        self,
        db: AsyncSession,
        execution_id: str,
        *,
        runtime_ms: int | None = None,
        metrics: dict | None = None,
        error_message: str | None = None,
    ) -> Execution | None:

        execution = await self.get_execution_by_id(db, execution_id)
        if not execution:
            return None

        if runtime_ms is not None:
            execution.runtime_ms = runtime_ms

        if metrics is not None:
            execution.metrics = metrics

        if error_message is not None:
            execution.error_message = error_message

        await db.commit()
        await db.refresh(execution)

        return execution

    # ------------------------------------------------------------------ #
    # Deletion                                                            #
    # ------------------------------------------------------------------ #

    async def delete_execution(
        self,
        db: AsyncSession,
        execution_id: str,
    ) -> bool:

        execution = await self.get_execution_by_id(db, execution_id)
        if not execution:
            return False

        await db.delete(execution)
        await db.commit()

        return True