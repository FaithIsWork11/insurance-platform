"""convert users.id to uuid and add defaults

Revision ID: 9864ab4326c1
Revises: e0132b3b624c
Create Date: 2026-02-24 00:50:47.287047
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9864ab4326c1"
down_revision: Union[str, Sequence[str], None] = "e0132b3b624c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Enterprise migration:
    - Enable pgcrypto for gen_random_uuid()
    - Convert users.id from varchar(36) UUID-string -> native uuid
    - Add DB default so inserts never produce NULL ids
    """

    # 1) Enable extension for UUID generation (safe if already enabled)
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # 2) Convert existing id values (uuid text) into native uuid
    #    (assumes your users.id values are valid UUID strings)
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN id TYPE uuid
        USING id::uuid;
        """
    )

    # 3) Set DB-side default to generate UUIDs automatically
    op.alter_column(
        "users",
        "id",
        server_default=sa.text("gen_random_uuid()"),
        existing_nullable=False,
    )


def downgrade() -> None:
    """
    Reverse:
    - Remove default
    - Convert users.id back to varchar(36)
    """

    op.alter_column(
        "users",
        "id",
        server_default=None,
        existing_nullable=False,
    )

    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN id TYPE varchar(36)
        USING id::text;
        """
    )

    # NOTE: We do NOT drop pgcrypto because other tables may rely on it.