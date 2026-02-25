from datetime import datetime
from sqlalchemy.orm import Session
from backend.models.task import Task
from backend.core.enums import TaskStatus


class TaskRepository:

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
    ) -> Task:

        task = Task(
            user_id=user_id,
            name=name,
            task_type=task_type,
            input_payload=input_payload,
            priority=priority,
            model_version_id=model_version_id,
            status=TaskStatus.PENDING,
            submitted_at=datetime.utcnow(),
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        return task


    def get_task_by_id(self, db: Session, task_id: str) -> Task | None:
        return db.query(Task).filter(Task.id == task_id).first()


    def get_tasks_by_user(
        self,
        db: Session,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ):
        return (
            db.query(Task)
            .filter(Task.user_id == user_id)
            .order_by(Task.submitted_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )


    def list_tasks_by_status(
        self,
        db: Session,
        status: TaskStatus,
        skip: int = 0,
        limit: int = 50,
    ):
        return (
            db.query(Task)
            .filter(Task.status == status)
            .order_by(Task.priority.desc(), Task.submitted_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )


    def get_pending_tasks(self, db: Session, limit: int = 50):
        return self.list_tasks_by_status(db, TaskStatus.PENDING, limit=limit)


    def update_task_status(
        self,
        db: Session,
        task_id: str,
        status: TaskStatus,
    ) -> Task | None:

        task = self.get_task_by_id(db, task_id)
        if not task:
            return None

        task.status = status

        if status == TaskStatus.RUNNING and task.started_at is None:
            task.started_at = datetime.utcnow()

        if status in (TaskStatus.SUCCESS, TaskStatus.FAILED):
            task.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(task)
        return task


    def increment_retry_count(self, db: Session, task_id: str) -> Task | None:
        task = self.get_task_by_id(db, task_id)
        if not task:
            return None

        task.retry_count += 1
        db.commit()
        db.refresh(task)
        return task


    def delete_task(self, db: Session, task_id: str) -> bool:
        task = self.get_task_by_id(db, task_id)
        if not task:
            return False

        db.delete(task)
        db.commit()
        return True