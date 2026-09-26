import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base

if TYPE_CHECKING:
    from app.features.batteries.models import Battery


class TelemetryEventKind(str, enum.Enum):
    metric = "metric"
    log = "log"
    device_incident = "device_incident"


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    battery_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batteries.id", ondelete="CASCADE"),
        index=True,
    )
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    kind: Mapped[TelemetryEventKind] = mapped_column(
        Enum(TelemetryEventKind, name="telemetry_event_kind"),
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    battery: Mapped["Battery"] = relationship(back_populates="telemetry_events")


class BatteryMetricSnapshot(Base):
    __tablename__ = "battery_metric_snapshots"

    battery_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batteries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    soc_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    inverter_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    grid_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    backup_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    connectivity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fault_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    battery: Mapped["Battery"] = relationship(back_populates="metric_snapshot")
