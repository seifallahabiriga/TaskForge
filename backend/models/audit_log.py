import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, generate_uuid


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    user_id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id")
    )

    action: Mapped[str] = mapped_column(sa.String)

    entity_type: Mapped[str] = mapped_column(sa.String)

    entity_id: Mapped[str] = mapped_column(sa.UUID)

    metadata: Mapped[dict | None] = mapped_column(
        sa.JSON,
        nullable=True
    )

    ip_address: Mapped[str] = mapped_column(sa.String)

    timestamp: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime,
        server_default=sa.func.now()
    )