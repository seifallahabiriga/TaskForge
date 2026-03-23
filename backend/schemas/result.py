from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class ResultResponse(BaseModel):
    id: UUID
    task_id: UUID
    execution_id: UUID | None
    storage_path: str | None
    output_summary: dict | None
    created_at: datetime

    class Config:
        from_attributes = True