import uuid
import os
import json
from sqlalchemy.orm import Session

from backend.repositories.task_repository import TaskRepository
from backend.core.enums import TaskStatus
from backend.services.task_lifecycle_engine import TaskLifecycleEngine
from backend.core.exceptions import (
    TaskNotFoundError,
    TaskExecutionError,
    TaskPermissionError
)


class TaskService:

    def __init__(self):
        self.task_repo = TaskRepository()
        self.engine = TaskLifecycleEngine()


    # Task Creation
    def create_task(
        self,
        db: Session,
        *,
        user_id: int,
        task_type: str,
        payload: dict,
    ):

        # Simulate artifact storage (No S3/Blob yet)
        artifact_id = str(uuid.uuid4())

        storage_dir = "storage/tasks"
        os.makedirs(storage_dir, exist_ok=True)

        payload_path = f"{storage_dir}/{artifact_id}.json"

        
        with open(payload_path, "w") as f:
            json.dump(payload, f)

        task = self.task_repo.create_task(
            db,
            user_id=user_id,
            task_type=task_type,
            payload_path=payload_path,
            priority=1
        )

        return task


    # Lifecycle Execution (Simulation Only)
    def start_task_execution(
        self,
        db: Session,
        *,
        task_id: int
    ):
        task = self.task_repo.get_task_by_id(db, task_id)

        if not task:
            raise TaskNotFoundError("Task not found")

        self.engine.validate_transition(
            task.status,
            TaskStatus.RUNNING
        )

        return self.task_repo.update_task_status(
            db,
            task_id,
            TaskStatus.RUNNING
        )


    def complete_task_execution(self, 
        db: Session, 
        *, 
        task_id: int, 
        result: dict
    ):

        task = self.task_repo.get_task_by_id(db, task_id)

        if not task:
            raise TaskNotFoundError("Task not found")

        self.engine.validate_transition(
            task.status,
            TaskStatus.COMPLETED
        )

        # Save result artifact
        result_dir = "storage/results"
        os.makedirs(result_dir, exist_ok=True)

        result_file = f"{result_dir}/{uuid.uuid4()}.json"

        with open(result_file, "w") as f:
            json.dump(result, f)

        self.task_repo.update_task_result(
            db,
            task_id,
            result_file
        )

        return self.task_repo.update_task_status(
            db,
            task_id,
            TaskStatus.COMPLETED
        )


    def fail_task_execution(
        self,
        db: Session,
        *,
        task_id: int,
        error_message: str
    ):

        task = self.task_repo.get_task_by_id(db, task_id)

        if not task:
            raise TaskNotFoundError("Task not found")

        task.error_message = error_message
        db.commit()
        db.refresh(task)

        return self.task_repo.update_task_status(
            db,
            task_id,
            TaskStatus.FAILED
        )

    # Queries
    def get_task(self, db: Session, task_id: int):
        return self.task_repo.get_task_by_id(db, task_id)


    def get_user_tasks(self, db: Session, user_id: int):
        return self.task_repo.get_tasks_by_user(db, user_id)