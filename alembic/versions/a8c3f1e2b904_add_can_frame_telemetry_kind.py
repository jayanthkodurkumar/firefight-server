"""add can_frame telemetry kind (historical; optional enum value)

Revision ID: a8c3f1e2b904
Revises: 2f00228655b3
Create Date: 2026-09-26 16:20:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "a8c3f1e2b904"
down_revision: Union[str, Sequence[str], None] = "2f00228655b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE telemetry_event_kind ADD VALUE IF NOT EXISTS 'can_frame'")


def downgrade() -> None:
    pass
