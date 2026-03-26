import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, generate_uuid


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )
    user_id: Mapped[str | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id"),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(sa.String)        # e.g. "task.created"

    entity_type: Mapped[str] = mapped_column(sa.String)   # e.g. "task"

    entity_id: Mapped[str | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )

    event_metadata: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    
    timestamp: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime,
        server_default=sa.func.now(),
    )