from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    event_metadata: dict | None
    ip_address: str | None
    timestamp: datetime

    class Config:
        from_attributes = True