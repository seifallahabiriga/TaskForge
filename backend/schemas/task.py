from pydantic import BaseModel
from datetime import datetime
from backend.core.enums import TaskType, TaskStatus


class TaskCreate(BaseModel):
    name: str
    task_type: TaskType
    priority: int = 0
    model_version_id: str | None = None
    input_payload: dict


class TaskStatusResponse(BaseModel):
    id: str
    status: TaskStatus
    error_message: str | None
    retry_count: int

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: str
    name: str
    task_type: TaskType
    priority: int
    status: TaskStatus
    retry_count: int
    max_retries: int
    error_message: str | None
    submitted_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    class Config:
        from_attributes = True