import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, generate_uuid
from backend.core.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    email: Mapped[str] = mapped_column(
        sa.String,
        unique=True,
        index=True
    )

    username: Mapped[str] = mapped_column(
        sa.String,
        unique=True
    )

    password_hash: Mapped[str] = mapped_column(sa.String)

    role: Mapped[UserRole] = mapped_column(
        sa.Enum(UserRole),
        default=UserRole.USER
    )

    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True
    )

    last_login_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime,
        nullable=True
    )

    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime,
        server_default=sa.func.now()
    )

    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime,
        server_default=sa.func.now(),
        onupdate=sa.func.now()
    )