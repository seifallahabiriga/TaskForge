from pydantic import BaseModel
from datetime import datetime


class ModelVersionResponse(BaseModel):
    id: str
    name: str
    version_tag: str
    framework: str
    artifact_path: str
    checksum: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True