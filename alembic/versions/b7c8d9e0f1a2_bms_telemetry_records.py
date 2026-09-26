"""BMS JSON Lines telemetry records replace generic telemetry_events."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "f0b1c2d3e4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "telemetry_events" in tables:
        op.execute("DROP INDEX IF EXISTS ix_telemetry_events_event_time")
        op.execute("DROP INDEX IF EXISTS ix_telemetry_events_event_id")
        op.execute("DROP INDEX IF EXISTS ix_telemetry_events_bms_pk")
        op.execute("DROP INDEX IF EXISTS ix_telemetry_events_battery_pk")
        op.drop_table("telemetry_events")
    op.execute("DROP TYPE IF EXISTS telemetry_event_kind")

    if "bms_telemetry_records" not in tables:
        op.create_table(
            "bms_telemetry_records",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("record_id", sa.String(length=160), nullable=False),
            sa.Column("bms_pk", sa.UUID(), nullable=False),
            sa.Column("unit_id", sa.String(length=16), nullable=False),
            sa.Column("site_id", sa.String(length=64), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("t_s", sa.Integer(), nullable=True),
            sa.Column("signals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column(
                "ingested_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["bms_pk"], ["bms_units.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_bms_telemetry_records_bms_pk"), "bms_telemetry_records", ["bms_pk"], unique=False
        )
        op.create_index(
            op.f("ix_bms_telemetry_records_record_id"), "bms_telemetry_records", ["record_id"], unique=True
        )
        op.create_index(
            op.f("ix_bms_telemetry_records_recorded_at"),
            "bms_telemetry_records",
            ["recorded_at"],
            unique=False,
        )
        op.create_index(
            op.f("ix_bms_telemetry_records_site_id"), "bms_telemetry_records", ["site_id"], unique=False
        )
        op.create_index(
            op.f("ix_bms_telemetry_records_unit_id"), "bms_telemetry_records", ["unit_id"], unique=False
        )

    if "bms_metric_snapshots" in tables:
        op.drop_table("bms_metric_snapshots")

    op.create_table(
        "bms_metric_snapshots",
        sa.Column("bms_pk", sa.UUID(), nullable=False),
        sa.Column("soc_pct", sa.Float(), nullable=True),
        sa.Column("pack_voltage_v", sa.Float(), nullable=True),
        sa.Column("pack_current_a", sa.Float(), nullable=True),
        sa.Column("tcell_max_c", sa.Float(), nullable=True),
        sa.Column("bms_state", sa.String(length=32), nullable=True),
        sa.Column("hub_mode", sa.String(length=32), nullable=True),
        sa.Column("fault_bits", sa.Integer(), nullable=True),
        sa.Column("last_record_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["bms_pk"], ["bms_units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("bms_pk"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "bms_metric_snapshots" in tables:
        op.drop_table("bms_metric_snapshots")

    op.create_table(
        "bms_metric_snapshots",
        sa.Column("bms_pk", sa.UUID(), nullable=False),
        sa.Column("soc_pct", sa.Float(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("inverter_status", sa.String(length=32), nullable=True),
        sa.Column("grid_status", sa.String(length=32), nullable=True),
        sa.Column("backup_available", sa.Boolean(), nullable=True),
        sa.Column("connectivity", sa.String(length=32), nullable=True),
        sa.Column("fault_code", sa.String(length=64), nullable=True),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["bms_pk"], ["bms_units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("bms_pk"),
    )

    if "bms_telemetry_records" in tables:
        op.drop_index(op.f("ix_bms_telemetry_records_unit_id"), table_name="bms_telemetry_records")
        op.drop_index(op.f("ix_bms_telemetry_records_site_id"), table_name="bms_telemetry_records")
        op.drop_index(op.f("ix_bms_telemetry_records_recorded_at"), table_name="bms_telemetry_records")
        op.drop_index(op.f("ix_bms_telemetry_records_record_id"), table_name="bms_telemetry_records")
        op.drop_index(op.f("ix_bms_telemetry_records_bms_pk"), table_name="bms_telemetry_records")
        op.drop_table("bms_telemetry_records")

    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("bms_pk", sa.UUID(), nullable=False),
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
        sa.ForeignKeyConstraint(["bms_pk"], ["bms_units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_telemetry_events_bms_pk"), "telemetry_events", ["bms_pk"], unique=False)
    op.create_index(op.f("ix_telemetry_events_event_id"), "telemetry_events", ["event_id"], unique=True)
    op.create_index(op.f("ix_telemetry_events_event_time"), "telemetry_events", ["event_time"], unique=False)
