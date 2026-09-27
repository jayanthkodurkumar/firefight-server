"""Add rejected ticket status and rejection metadata."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i8c9d0e1f2a4"
down_revision: Union[str, Sequence[str], None] = "h7b8c9d0e1f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN "
        "ALTER TYPE ticket_status ADD VALUE 'rejected'; "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.add_column("tickets", sa.Column("rejected_by_user_id", sa.UUID(), nullable=True))
    op.add_column("tickets", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tickets", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_tickets_rejected_by_user_id",
        "tickets",
        "users",
        ["rejected_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_tickets_rejected_by_user_id",
        "tickets",
        ["rejected_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.execute("UPDATE tickets SET status = 'open' WHERE status::text = 'rejected'")
    op.drop_index("ix_tickets_rejected_by_user_id", table_name="tickets")
    op.drop_constraint("fk_tickets_rejected_by_user_id", "tickets", type_="foreignkey")
    op.drop_column("tickets", "rejection_reason")
    op.drop_column("tickets", "rejected_at")
    op.drop_column("tickets", "rejected_by_user_id")
