"""Drop CAN log tables and restore telemetry_events + battery_metric_snapshots."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e9f4c2a81b0d"
down_revision: Union[str, Sequence[str], None] = "c7d2a91f0e3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(connection) -> set[str]:
    return set(sa.inspect(connection).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    tables = _table_names(bind)

    for name in (
        "can_log_frames",
        "can_log_captures",
        "can_databases",
    ):
        if name in tables:
            op.drop_table(name)
            tables.remove(name)

    if "telemetry_events" in tables and "battery_metric_snapshots" in tables:
        return

    if "telemetry_events" in tables:
        op.drop_index(op.f("ix_telemetry_events_event_time"), table_name="telemetry_events")
        op.drop_index(op.f("ix_telemetry_events_event_id"), table_name="telemetry_events")
        op.drop_index(op.f("ix_telemetry_events_battery_pk"), table_name="telemetry_events")
        op.drop_table("telemetry_events")
    if "battery_metric_snapshots" in tables:
        op.drop_table("battery_metric_snapshots")

    op.execute("DROP TYPE IF EXISTS telemetry_event_kind")

    op.create_table(
        "battery_metric_snapshots",
        sa.Column("battery_pk", sa.UUID(), nullable=False),
        sa.Column("soc_pct", sa.Float(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("inverter_status", sa.String(length=32), nullable=True),
        sa.Column("grid_status", sa.String(length=32), nullable=True),
        sa.Column("backup_available", sa.Boolean(), nullable=True),
        sa.Column("connectivity", sa.String(length=32), nullable=True),
        sa.Column("fault_code", sa.String(length=64), nullable=True),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["battery_pk"], ["batteries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("battery_pk"),
    )
    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("battery_pk", sa.UUID(), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("metric", "log", "device_incident", name="telemetry_event_kind"),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["battery_pk"], ["batteries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_telemetry_events_battery_pk"), "telemetry_events", ["battery_pk"], unique=False)
    op.create_index(op.f("ix_telemetry_events_event_id"), "telemetry_events", ["event_id"], unique=True)
    op.create_index(op.f("ix_telemetry_events_event_time"), "telemetry_events", ["event_time"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    tables = _table_names(bind)

    if "telemetry_events" in tables:
        op.drop_index(op.f("ix_telemetry_events_event_time"), table_name="telemetry_events")
        op.drop_index(op.f("ix_telemetry_events_event_id"), table_name="telemetry_events")
        op.drop_index(op.f("ix_telemetry_events_battery_pk"), table_name="telemetry_events")
        op.drop_table("telemetry_events")
    if "battery_metric_snapshots" in tables:
        op.drop_table("battery_metric_snapshots")
    op.execute("DROP TYPE IF EXISTS telemetry_event_kind")

    if "can_log_frames" not in tables:
        op.create_table(
            "can_log_frames",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("frame_id", sa.String(length=160), nullable=False),
            sa.Column("battery_pk", sa.UUID(), nullable=False),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("iface", sa.String(length=32), nullable=False),
            sa.Column("can_id", sa.String(length=8), nullable=False),
            sa.Column("data_hex", sa.String(length=16), nullable=False),
            sa.Column(
                "ingested_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["battery_pk"], ["batteries.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_can_log_frames_battery_pk"), "can_log_frames", ["battery_pk"], unique=False)
        op.create_index(op.f("ix_can_log_frames_can_id"), "can_log_frames", ["can_id"], unique=False)
        op.create_index(op.f("ix_can_log_frames_captured_at"), "can_log_frames", ["captured_at"], unique=False)
        op.create_index(op.f("ix_can_log_frames_frame_id"), "can_log_frames", ["frame_id"], unique=True)
