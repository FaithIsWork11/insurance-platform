"""convert leads.id to uuid and add defaults

Revision ID: 923bb45bab51
Revises: 9864ab4326c1
Create Date: 2026-02-24 00:57:33.664736
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "923bb45bab51"
down_revision: Union[str, Sequence[str], None] = "9864ab4326c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Enterprise migration:
    - Ensure pgcrypto exists for gen_random_uuid()
    - Convert leads.id from varchar(36) UUID-string -> native uuid
    - Add DB default to prevent NULL id inserts
    """

    # 1) Enable extension for UUID generation (safe if already enabled)
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # 2) Convert existing leads.id values (uuid text) into native uuid
    op.execute(
        """
        ALTER TABLE leads
        ALTER COLUMN id TYPE uuid
        USING id::uuid;
        """
    )

    # 3) Set DB-side default to generate UUIDs automatically
    op.alter_column(
        "leads",
        "id",
        server_default=sa.text("gen_random_uuid()"),
        existing_nullable=False,
    )


def downgrade() -> None:
    """
    Reverse:
    - Remove default
    - Convert leads.id back to varchar(36)
    """

    op.alter_column(
        "leads",
        "id",
        server_default=None,
        existing_nullable=False,
    )

    op.execute(
        """
        ALTER TABLE leads
        ALTER COLUMN id TYPE varchar(36)
        USING id::text;
        """
    )