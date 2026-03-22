from pydantic import BaseModel
from datetime import datetime


class ModelVersionResponse(BaseModel):
    id: str
    name: str
    model_id: str
    provider: str
    task_type: str
    config: dict | None
    is_default: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ModelVersionListResponse(BaseModel):
    items: list[ModelVersionResponse]
    total: int