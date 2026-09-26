"""Rename batteries domain to BMS units (unit_id + site_id)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f0b1c2d3e4a5"
down_revision: Union[str, Sequence[str], None] = "e9f4c2a81b0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(connection) -> set[str]:
    return set(sa.inspect(connection).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)

    if "bms_units" in tables:
        return
    if "batteries" not in tables:
        raise RuntimeError("Expected batteries table before BMS migration")

    op.rename_table("batteries", "bms_units")
    op.alter_column("bms_units", "battery_id", new_column_name="site_id")
    op.add_column("bms_units", sa.Column("unit_id", sa.String(length=16), nullable=True))
    op.execute(
        """
        UPDATE bms_units
        SET unit_id = COALESCE(extra->>'fleet_unit', site_id)
        """
    )
    op.alter_column("bms_units", "unit_id", nullable=False)

    op.drop_index("ix_batteries_battery_id", table_name="bms_units")
    op.create_index(op.f("ix_bms_units_unit_id"), "bms_units", ["unit_id"], unique=True)
    op.create_index(op.f("ix_bms_units_site_id"), "bms_units", ["site_id"], unique=True)

    op.alter_column("telemetry_events", "battery_pk", new_column_name="bms_pk")
    op.execute("ALTER INDEX IF EXISTS ix_telemetry_events_battery_pk RENAME TO ix_telemetry_events_bms_pk")

    op.alter_column("incidents", "battery_pk", new_column_name="bms_pk")
    op.execute("ALTER INDEX IF EXISTS ix_incidents_battery_pk RENAME TO ix_incidents_bms_pk")

    op.alter_column("service_records", "battery_pk", new_column_name="bms_pk")

    if "battery_metric_snapshots" in tables:
        op.rename_table("battery_metric_snapshots", "bms_metric_snapshots")
        op.alter_column("bms_metric_snapshots", "battery_pk", new_column_name="bms_pk")


def downgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)

    if "batteries" in tables:
        return
    if "bms_units" not in tables:
        return

    if "bms_metric_snapshots" in tables:
        op.alter_column("bms_metric_snapshots", "bms_pk", new_column_name="battery_pk")
        op.rename_table("bms_metric_snapshots", "battery_metric_snapshots")

    op.alter_column("service_records", "bms_pk", new_column_name="battery_pk")
    op.alter_column("incidents", "bms_pk", new_column_name="battery_pk")
    op.execute("ALTER INDEX IF EXISTS ix_incidents_bms_pk RENAME TO ix_incidents_battery_pk")
    op.alter_column("telemetry_events", "bms_pk", new_column_name="battery_pk")
    op.execute("ALTER INDEX IF EXISTS ix_telemetry_events_bms_pk RENAME TO ix_telemetry_events_battery_pk")

    op.drop_index(op.f("ix_bms_units_site_id"), table_name="bms_units")
    op.drop_index(op.f("ix_bms_units_unit_id"), table_name="bms_units")
    op.drop_column("bms_units", "unit_id")
    op.alter_column("bms_units", "site_id", new_column_name="battery_id")
    op.create_index("ix_batteries_battery_id", "bms_units", ["battery_id"], unique=True)
    op.rename_table("bms_units", "batteries")
