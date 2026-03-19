from pydantic import BaseModel
from datetime import datetime
from backend.core.enums import ExecutionStatus


class ExecutionResponse(BaseModel):
    id: str
    task_id: str
    worker_id: str | None
    status: ExecutionStatus
    attempt_number: int
    runtime_ms: int | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None

    class Config:
        from_attributes = True