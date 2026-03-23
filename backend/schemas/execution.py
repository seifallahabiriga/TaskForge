from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from backend.core.enums import ExecutionStatus


class ExecutionResponse(BaseModel):
    id: UUID
    task_id: UUID
    worker_id: UUID | None
    status: ExecutionStatus
    attempt_number: int
    runtime_ms: int | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None

    class Config:
        from_attributes = True