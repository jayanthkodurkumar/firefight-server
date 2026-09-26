import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base

if TYPE_CHECKING:
    from app.features.batteries.models import Battery
    from app.features.rules.models import AlertRule
    from app.features.technicians.models import Technician


class IncidentStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class IncidentEventSource(str, enum.Enum):
    rule = "rule"
    human = "human"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    battery_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batteries.id", ondelete="CASCADE"),
        index=True,
    )
    rule_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("alert_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status"),
        default=IncidentStatus.open,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(64), index=True)
    fault_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(16), nullable=True)
    priority_rationale: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    rca: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    assigned_technician_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("technicians.id", ondelete="SET NULL"),
        nullable=True,
    )
    state_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    battery: Mapped["Battery"] = relationship(back_populates="incidents")
    rule: Mapped["AlertRule | None"] = relationship()
    assigned_technician: Mapped["Technician | None"] = relationship(back_populates="incidents")
    events: Mapped[list["IncidentEvent"]] = relationship(back_populates="incident")


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64))
    source: Mapped[IncidentEventSource] = mapped_column(
        Enum(IncidentEventSource, name="incident_event_source"),
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="events")
