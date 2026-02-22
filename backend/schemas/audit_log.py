from pydantic import BaseModel
from datetime import datetime


class AuditLogResponse(BaseModel):
    id: str
    user_id: str
    action: str
    entity_type: str
    entity_id: str
    metadata: dict | None
    ip_address: str
    timestamp: datetime

    class Config:
        from_attributes = True