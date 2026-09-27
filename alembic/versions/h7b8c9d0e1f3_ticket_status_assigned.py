"""Add assigned value to ticket_status enum."""

from typing import Sequence, Union

from alembic import op

revision: str = "h7b8c9d0e1f3"
down_revision: Union[str, Sequence[str], None] = "g6a7b8c9d0e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN "
        "ALTER TYPE ticket_status ADD VALUE 'assigned'; "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "UPDATE tickets SET status = 'assigned' "
        "WHERE assigned_technician_id IS NOT NULL AND status::text = 'open'"
    )


def downgrade() -> None:
    op.execute("UPDATE tickets SET status = 'open' WHERE status::text = 'assigned'")
    # PostgreSQL cannot drop enum values easily; leave 'assigned' on downgrade.
