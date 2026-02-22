import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, generate_uuid
from core.enums import ExecutionStatus


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    task_id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("tasks.id")
    )

    worker_id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("workers.id")
    )

    status: Mapped[ExecutionStatus] = mapped_column(
        sa.Enum(ExecutionStatus)
    )

    attempt_number: Mapped[int] = mapped_column(sa.Integer)

    started_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime)

    finished_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime,
        nullable=True
    )

    runtime_seconds: Mapped[float | None] = mapped_column(
        sa.Float,
        nullable=True
    )

    error_message: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True
    )