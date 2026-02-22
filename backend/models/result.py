import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, generate_uuid


class Result(Base):
    __tablename__ = "results"

    id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    task_id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("tasks.id"),
        nullable=False
    )

    execution_id: Mapped[str | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("executions.id"),
        nullable=True
    )

    storage_path: Mapped[str] = mapped_column(
        sa.String,
        nullable=False
    )

    output_summary: Mapped[dict | None] = mapped_column(
        sa.JSON,
        nullable=True
    )

    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime,
        server_default=sa.func.now()
    )