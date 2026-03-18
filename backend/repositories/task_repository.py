from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.task import Task
from backend.core.enums import TaskStatus


class TaskRepository:

    async def create_task(
        self,
        db: AsyncSession,
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
        await db.commit()
        await db.refresh(task)

        return task


    async def get_task_by_id(self, db: AsyncSession, task_id: str) -> Task | None:
        result = await db.execute(select(Task).where(Task.id == task_id))
        return result.scalars().first()


    async def get_tasks_by_user(
        self,
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ):
        result = await db.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(Task.submitted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()


    async def list_tasks_by_status(
        self,
        db: AsyncSession,
        status: TaskStatus,
        skip: int = 0,
        limit: int = 50,
    ):
        result = await db.execute(
            select(Task)
            .where(Task.status == status)
            .order_by(Task.priority.desc(), Task.submitted_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()


    async def get_pending_tasks(self, db: AsyncSession, limit: int = 50):
        return await self.list_tasks_by_status(db, TaskStatus.PENDING, limit=limit)


    async def update_task_status(
        self,
        db: AsyncSession,
        task_id: str,
        status: TaskStatus,
    ) -> Task | None:

        task = await self.get_task_by_id(db, task_id)
        if not task:
            return None

        task.status = status

        if status == TaskStatus.RUNNING and task.started_at is None:
            task.started_at = datetime.utcnow()

        if status in (TaskStatus.SUCCESS, TaskStatus.FAILED):
            task.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(task)
        return task


    async def increment_retry_count(self, db: AsyncSession, task_id: str) -> Task | None:
        task = await self.get_task_by_id(db, task_id)
        if not task:
            return None

        task.retry_count += 1
        await db.commit()
        await db.refresh(task)
        return task


    async def delete_task(self, db: AsyncSession, task_id: str) -> bool:
        task = await self.get_task_by_id(db, task_id)
        if not task:
            return False

        await db.delete(task)
        await db.commit()
        
        return True