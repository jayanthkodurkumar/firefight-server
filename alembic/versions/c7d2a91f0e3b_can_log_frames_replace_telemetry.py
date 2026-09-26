"""can_log_frames replace telemetry_events (historical revision stub)

The original upgrade created ``can_log_frames`` and dropped telemetry tables.
That migration may already be applied on your database. The real rollback lives
in ``e9f4c2a81b0d_drop_can_restore_telemetry``.

Revision ID: c7d2a91f0e3b
Revises: a8c3f1e2b904
Create Date: 2026-09-26 16:30:00.000000

"""

from typing import Sequence, Union

revision: str = "c7d2a91f0e3b"
down_revision: Union[str, Sequence[str], None] = "a8c3f1e2b904"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
