import socket
import time
from datetime import datetime

from celery import Task
from sqlalchemy.orm import Session

from backend.queue.celery_app import celery_app
from backend.db.session import SyncSessionLocal
from backend.core.config import settings
from backend.models.task import Task as DBTask
from backend.models.execution import Execution
from backend.core.enums import ExecutionStatus, TaskStatus

# Optional: Add any pure AI inference logic here or in a separate job_runner.py module
# that does not require DB access.
def run_ai_workload(task_type: str, payload: dict) -> dict:
    if task_type == "echo":
        return {"output": payload}
    elif task_type == "sum":
        numbers = payload.get("numbers", [])
        return {"output": sum(numbers)}
    else:
        raise ValueError(f"Unsupported task type: {task_type}")


@celery_app.task(
    bind=True,
    name="app.queue.tasks.execute_ai_task",
    max_retries=settings.CELERY_MAX_RETRIES,
    default_retry_delay=settings.CELERY_RETRY_DELAY_SECONDS,
)
def execute_ai_task(self, task_id: str, payload: dict):

    worker_id = socket.gethostname()
    start_time = time.time()

    # Open a synchronous database session
    with SyncSessionLocal() as db:
        
        # 1. Fetch the Task
        task = db.query(DBTask).filter(DBTask.id == task_id).first()
        if not task:
            # We cannot proceed if task doesn't exist
            return {"error": "Task not found"}

        # 2. Create Execution Record
        execution = Execution(
            task_id=task_id,
            worker_id=worker_id,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        db.add(execution)
        
        # Update Task Status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        db.commit()

        # 3. Core Compute Logic (No DB access needed here)
        try:
            result = run_ai_workload(task.task_type, payload)

            # 4. Handle Success state
            runtime_ms = int((time.time() - start_time) * 1000)
            
            execution.status = ExecutionStatus.SUCCESS
            execution.completed_at = datetime.utcnow()
            execution.runtime_ms = runtime_ms
            execution.metrics = {"worker_id": worker_id}

            task.status = TaskStatus.SUCCESS
            task.completed_at = datetime.utcnow()
            
            db.commit()
            return result

        except Exception as exc:
            # 5. Handle Failure state
            runtime_ms = int((time.time() - start_time) * 1000)
            
            execution.status = ExecutionStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.error_message = str(exc)
            execution.runtime_ms = runtime_ms
            db.commit() # commit execution failure early
            
            # Retry Logic
            try:
                if task.retry_count >= task.max_retries:
                    raise self.MaxRetriesExceededError("Max retries exceeded")
            
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                db.commit()
                
                # Retry celery task
                raise self.retry(exc=exc)
                
            except self.MaxRetriesExceededError:
                task.status = TaskStatus.FAILED
                task.error_message = str(exc)
                db.commit()
                raise