from pydantic import BaseModel
from datetime import datetime
from backend.core.enums import WorkerStatus, WorkerType


class WorkerResponse(BaseModel):
    id: str
    hostname: str
    ip_address: str | None
    status: WorkerStatus
    worker_type: WorkerType
    capacity: int
    last_heartbeat: datetime

    class Config:
        from_attributes = True