"""ticket_policy, ticket_eval_state, and tickets tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    op.execute(
        "DO $$ BEGIN CREATE TYPE ticket_status AS ENUM ('open', 'resolved'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    ticket_status = postgresql.ENUM(
        "open",
        "resolved",
        name="ticket_status",
        create_type=False,
    )

    if "ticket_policy" not in tables:
        op.create_table(
            "ticket_policy",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=True),
            sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("rule_type", sa.String(length=64), nullable=True),
            sa.Column("definition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ticket_policy_enabled", "ticket_policy", ["enabled"], unique=False)

    if "ticket_eval_state" not in tables:
        op.create_table(
            "ticket_eval_state",
            sa.Column("bms_pk", sa.UUID(), nullable=False),
            sa.Column("rule_id", sa.String(length=64), nullable=False),
            sa.Column(
                "state",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["bms_pk"], ["bms_units.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["rule_id"], ["ticket_policy.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("bms_pk", "rule_id"),
        )

    if "tickets" not in tables:
        op.create_table(
            "tickets",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("ticket_id", sa.String(length=32), nullable=False),
            sa.Column("bms_pk", sa.UUID(), nullable=False),
            sa.Column("telemetry_record_pk", sa.UUID(), nullable=False),
            sa.Column("primary_rule_id", sa.String(length=64), nullable=True),
            sa.Column("fired_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("severity", sa.String(length=8), nullable=False),
            sa.Column("priority", sa.String(length=8), nullable=False),
            sa.Column("category", sa.String(length=64), nullable=True),
            sa.Column("skill", sa.String(length=64), nullable=True),
            sa.Column("dtc", sa.String(length=32), nullable=True),
            sa.Column("hint", sa.Text(), nullable=True),
            sa.Column("status", ticket_status, server_default="open", nullable=False),
            sa.Column("state_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["bms_pk"], ["bms_units.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["primary_rule_id"], ["ticket_policy.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(
                ["telemetry_record_pk"],
                ["bms_telemetry_records.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("ticket_id"),
        )
        op.create_index("ix_tickets_bms_pk", "tickets", ["bms_pk"], unique=False)
        op.create_index("ix_tickets_recorded_at", "tickets", ["recorded_at"], unique=False)
        op.create_index("ix_tickets_status", "tickets", ["status"], unique=False)
        op.create_index(
            "ix_tickets_telemetry_record_pk",
            "tickets",
            ["telemetry_record_pk"],
            unique=False,
        )
        op.create_index("ix_tickets_ticket_id", "tickets", ["ticket_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tickets_ticket_id", table_name="tickets")
    op.drop_index("ix_tickets_telemetry_record_pk", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_recorded_at", table_name="tickets")
    op.drop_index("ix_tickets_bms_pk", table_name="tickets")
    op.drop_table("tickets")
    op.drop_table("ticket_eval_state")
    op.drop_index("ix_ticket_policy_enabled", table_name="ticket_policy")
    op.drop_table("ticket_policy")
    op.execute("DROP TYPE IF EXISTS ticket_status")
