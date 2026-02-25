import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, generate_uuid
from backend.core.enums import WorkerStatus, WorkerType


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    hostname: Mapped[str] = mapped_column(sa.String)

    ip_address: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True
    )

    status: Mapped[WorkerStatus] = mapped_column(
        sa.Enum(WorkerStatus),
        default=WorkerStatus.ONLINE
    )

    worker_type: Mapped[WorkerType] = mapped_column(
        sa.Enum(WorkerType)
    )

    capacity: Mapped[int] = mapped_column(sa.Integer)

    last_heartbeat: Mapped[sa.DateTime] = mapped_column(sa.DateTime)

    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime,
        server_default=sa.func.now()
    )