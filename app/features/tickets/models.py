import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base

if TYPE_CHECKING:
    from app.features.bms.models import BmsUnit
    from app.features.telemetry.models import BmsTelemetryRecord


class TicketStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"


class TicketPolicy(Base):
    """One row per rule from rules.yaml, plus `_merge` for ticket_policy settings."""

    __tablename__ = "ticket_policy"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    rule_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class TicketEvalState(Base):
    """Per-unit streak / history for rules that need duration (for_s, rate, etc.)."""

    __tablename__ = "ticket_eval_state"

    bms_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bms_units.id", ondelete="CASCADE"),
        primary_key=True,
    )
    rule_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ticket_policy.id", ondelete="CASCADE"),
        primary_key=True,
    )
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Ticket(Base):
    """Ticket opened when a telemetry record matches ticket_policy rules."""

    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    bms_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bms_units.id", ondelete="CASCADE"),
        index=True,
    )
    telemetry_record_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bms_telemetry_records.id", ondelete="CASCADE"),
        index=True,
    )
    primary_rule_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ticket_policy.id", ondelete="SET NULL"),
        nullable=True,
    )
    fired_rules: Mapped[list[str]] = mapped_column(JSONB)
    severity: Mapped[str] = mapped_column(String(8))
    priority: Mapped[str] = mapped_column(String(8))
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    skill: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dtc: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status"),
        default=TicketStatus.open,
        index=True,
    )
    state_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bms_unit: Mapped["BmsUnit"] = relationship(back_populates="tickets")
    telemetry_record: Mapped["BmsTelemetryRecord"] = relationship(back_populates="tickets")
    primary_rule: Mapped["TicketPolicy | None"] = relationship()
