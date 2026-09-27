"""Add assigned_by_user_id to tickets."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g6a7b8c9d0e2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("assigned_by_user_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_tickets_assigned_by_user_id",
        "tickets",
        "users",
        ["assigned_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_tickets_assigned_by_user_id",
        "tickets",
        ["assigned_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tickets_assigned_by_user_id", table_name="tickets")
    op.drop_constraint("fk_tickets_assigned_by_user_id", "tickets", type_="foreignkey")
    op.drop_column("tickets", "assigned_by_user_id")
