# app/models/lead.py
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func, Boolean, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Lead(Base):
    __tablename__ = "leads"

    # Enterprise UUID primary key:
    # - ORM default: uuid.uuid4
    # - DB default: gen_random_uuid() (pgcrypto)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)

    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    state: Mapped[str | None] = mapped_column(String(50), nullable=True)

    coverage_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="NEW",
    )

    # NOTE (enterprise): this should eventually become assigned_to_user_id: UUID FK -> users.id
    # For now leaving as-is per your current schema.
    assigned_to: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ---- Soft delete (enterprise) ----
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )