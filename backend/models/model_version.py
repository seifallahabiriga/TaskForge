import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, generate_uuid


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    name: Mapped[str] = mapped_column(sa.String)

    version_tag: Mapped[str] = mapped_column(sa.String)

    framework: Mapped[str] = mapped_column(sa.String)

    artifact_path: Mapped[str] = mapped_column(sa.String)

    checksum: Mapped[str] = mapped_column(sa.String)

    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True
    )

    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime,
        server_default=sa.func.now()
    )