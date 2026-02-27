from datetime import datetime
from sqlalchemy.orm import Session

from backend.models.execution import Execution
from backend.core.enums import ExecutionStatus


class ExecutionRepository:

    # ------------------------------------------------------------------ #
    # Creation                                                            #
    # ------------------------------------------------------------------ #

    def create_execution(
        self,
        db: Session,
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
        db.commit()
        db.refresh(execution)

        return execution

    # ------------------------------------------------------------------ #
    # Queries                                                             #
    # ------------------------------------------------------------------ #

    def get_execution_by_id(
        self,
        db: Session,
        execution_id: str,
    ) -> Execution | None:
        return (
            db.query(Execution)
            .filter(Execution.id == execution_id)
            .first()
        )

    def get_executions_by_task(
        self,
        db: Session,
        task_id: str,
        skip: int = 0,
        limit: int = 100,
    ):
        return (
            db.query(Execution)
            .filter(Execution.task_id == task_id)
            .order_by(Execution.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_worker_executions(
        self,
        db: Session,
        worker_id: str,
        skip: int = 0,
        limit: int = 100,
    ):
        return (
            db.query(Execution)
            .filter(Execution.worker_id == worker_id)
            .order_by(Execution.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_executions_by_status(
        self,
        db: Session,
        status: ExecutionStatus,
        skip: int = 0,
        limit: int = 100,
    ):
        return (
            db.query(Execution)
            .filter(Execution.status == status)
            .order_by(Execution.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------ #
    # State Updates                                                        #
    # ------------------------------------------------------------------ #

    def update_execution_status(
        self,
        db: Session,
        execution_id: str,
        status: ExecutionStatus,
    ) -> Execution | None:

        execution = self.get_execution_by_id(db, execution_id)
        if not execution:
            return None

        execution.status = status

        if status == ExecutionStatus.RUNNING and execution.started_at is None:
            execution.started_at = datetime.utcnow()

        if status in (ExecutionStatus.SUCCESS, ExecutionStatus.FAILED):
            execution.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(execution)

        return execution

    def update_execution_metrics(
        self,
        db: Session,
        execution_id: str,
        *,
        runtime_ms: int | None = None,
        metrics: dict | None = None,
        error_message: str | None = None,
    ) -> Execution | None:

        execution = self.get_execution_by_id(db, execution_id)
        if not execution:
            return None

        if runtime_ms is not None:
            execution.runtime_ms = runtime_ms

        if metrics is not None:
            execution.metrics = metrics

        if error_message is not None:
            execution.error_message = error_message

        db.commit()
        db.refresh(execution)

        return execution

    # ------------------------------------------------------------------ #
    # Deletion                                                            #
    # ------------------------------------------------------------------ #

    def delete_execution(
        self,
        db: Session,
        execution_id: str,
    ) -> bool:

        execution = self.get_execution_by_id(db, execution_id)
        if not execution:
            return False

        db.delete(execution)
        db.commit()

        return True