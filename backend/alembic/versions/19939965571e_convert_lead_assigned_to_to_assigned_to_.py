"""convert lead assigned_to to assigned_to_user_id uuid fk

Revision ID: 19939965571e
Revises: 08875f3e912f
Create Date: 2026-03-13 19:19:17.474653

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "19939965571e"
down_revision: Union[str, Sequence[str], None] = "08875f3e912f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "leads",
        sa.Column(
            "assigned_to_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # Only backfill values that:
    # 1. are valid UUID text
    # 2. actually exist in users.id
    op.execute(
        """
        UPDATE leads
        SET assigned_to_user_id = assigned_to::uuid
        WHERE assigned_to IS NOT NULL
          AND assigned_to ~* '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
          AND assigned_to::uuid IN (
              SELECT id FROM users
          )
        """
    )

    op.create_foreign_key(
        "fk_leads_assigned_to_user_id_users",
        "leads",
        "users",
        ["assigned_to_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_column("leads", "assigned_to")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "leads",
        sa.Column("assigned_to", sa.String(length=100), nullable=True),
    )

    op.execute(
        """
        UPDATE leads
        SET assigned_to = assigned_to_user_id::text
        WHERE assigned_to_user_id IS NOT NULL
        """
    )

    op.drop_constraint(
        "fk_leads_assigned_to_user_id_users",
        "leads",
        type_="foreignkey",
    )

    op.drop_column("leads", "assigned_to_user_id")