import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, generate_uuid
from backend.core.enums import TaskType, TaskStatus


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    user_id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id")
    )

    name: Mapped[str] = mapped_column(sa.String)

    task_type: Mapped[TaskType] = mapped_column(
        sa.Enum(TaskType)
    )

    priority: Mapped[int] = mapped_column(
        sa.Integer,
        default=0
    )

    status: Mapped[TaskStatus] = mapped_column(
        sa.Enum(TaskStatus),
        default=TaskStatus.PENDING
    )

    model_version_id: Mapped[str | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("model_versions.id"),
        nullable=True
    )

    input_payload: Mapped[dict] = mapped_column(sa.JSON)

    error_message: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True
    )

    retry_count: Mapped[int] = mapped_column(sa.Integer, default=0)

    max_retries: Mapped[int] = mapped_column(sa.Integer, default=3)

    submitted_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime)

    started_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime,
        nullable=True
    )

    completed_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime,
        nullable=True
    )