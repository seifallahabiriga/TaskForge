from sqlalchemy.orm import Session
from backend.models.task import Task
from backend.core.enums import TaskStatus


class TaskRepository:

    def create_task(
        self,
        db: Session,
        *,
        user_id: int,
        task_type: str,
        payload_path: str,
        priority: int | None = None
    ) -> Task:

        task = Task(
            user_id=user_id,
            task_type=task_type,
            payload_path=payload_path,
            priority=priority,
            status=TaskStatus.PENDING
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        return task


    def get_task_by_id(self, db: Session, task_id: int) -> Task | None:
        return db.query(Task).filter(Task.id == task_id).first()


    def get_tasks_by_user(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50
    ):
        return (
            db.query(Task)
            .filter(Task.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )


    def list_tasks_by_status(
        self,
        db: Session,
        status: TaskStatus,
        skip: int = 0,
        limit: int = 50
    ):
        return (
            db.query(Task)
            .filter(Task.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )


    def update_task_status(
        self,
        db: Session,
        task_id: int,
        status: TaskStatus
    ) -> Task | None:

        task = self.get_task_by_id(db, task_id)

        if not task:
            return None

        task.status = status

        db.commit()
        db.refresh(task)

        return task


    def update_task_result(
        self,
        db: Session,
        task_id: int,
        result_path: str
    ) -> Task | None:

        task = self.get_task_by_id(db, task_id)

        if not task:
            return None

        task.result_path = result_path

        db.commit()
        db.refresh(task)

        return task


    def delete_task(self, db: Session, task_id: int) -> bool:

        task = self.get_task_by_id(db, task_id)

        if not task:
            return False

        db.delete(task)
        db.commit()

        return True