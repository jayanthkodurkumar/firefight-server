import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base

if TYPE_CHECKING:
    from app.features.bms.models import BmsUnit
    from app.features.tickets.models import Ticket


class BmsTelemetryRecord(Base):
    """One decoded BMS telemetry row (1 Hz JSON Lines record per unit/site/ts)."""

    __tablename__ = "bms_telemetry_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    bms_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bms_units.id", ondelete="CASCADE"),
        index=True,
    )
    unit_id: Mapped[str] = mapped_column(String(16), index=True)
    site_id: Mapped[str] = mapped_column(String(64), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    t_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signals: Mapped[dict[str, Any]] = mapped_column(JSONB)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    bms_unit: Mapped["BmsUnit"] = relationship(back_populates="telemetry_records")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="telemetry_record")


class BmsMetricSnapshot(Base):
    """Latest derived metrics for coordinator views (updated on each ingested record)."""

    __tablename__ = "bms_metric_snapshots"

    bms_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bms_units.id", ondelete="CASCADE"),
        primary_key=True,
    )
    soc_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    pack_voltage_v: Mapped[float | None] = mapped_column(Float, nullable=True)
    pack_current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    tcell_max_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    bms_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hub_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fault_bits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_record_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    bms_unit: Mapped["BmsUnit"] = relationship(back_populates="metric_snapshot")
