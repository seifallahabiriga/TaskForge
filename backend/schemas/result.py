from pydantic import BaseModel
from datetime import datetime


class ResultResponse(BaseModel):
    id: str
    task_id: str
    execution_id: str | None
    storage_path: str
    output_summary: dict | None
    created_at: datetime

    class Config:
        from_attributes = True