import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from backend.db.base import Base, generate_uuid


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )
    name: Mapped[str] = mapped_column(sa.String)

    model_id: Mapped[str] = mapped_column(sa.String)           # e.g. "meta-llama/llama-3-8b-instruct"

    provider: Mapped[str] = mapped_column(sa.String)           # e.g. "openrouter", "huggingface"

    task_type: Mapped[str] = mapped_column(sa.String)          # e.g. "INFERENCE", "ANALYSIS"

    config: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)

    is_default: Mapped[bool] = mapped_column(sa.Boolean, default=False)

    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime,
        server_default=sa.func.now(),
    )