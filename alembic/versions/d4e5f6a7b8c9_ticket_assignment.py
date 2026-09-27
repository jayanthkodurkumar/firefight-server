"""Add technician assignment fields to tickets."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("assigned_technician_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column("dispatch_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_tickets_assigned_technician_id",
        "tickets",
        "technicians",
        ["assigned_technician_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_tickets_assigned_technician_id",
        "tickets",
        ["assigned_technician_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tickets_assigned_technician_id", table_name="tickets")
    op.drop_constraint("fk_tickets_assigned_technician_id", "tickets", type_="foreignkey")
    op.drop_column("tickets", "assigned_at")
    op.drop_column("tickets", "dispatch_notes")
    op.drop_column("tickets", "assigned_technician_id")
