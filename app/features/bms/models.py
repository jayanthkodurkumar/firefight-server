import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base

if TYPE_CHECKING:
    from app.features.incidents.models import Incident
    from app.features.telemetry.models import BmsMetricSnapshot, BmsTelemetryRecord
    from app.features.tickets.models import Ticket


class BmsUnit(Base):
    """Home BMS on the CAN bus (fleet unit + site), not a generic battery asset."""

    __tablename__ = "bms_units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    site_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    site_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    telemetry_records: Mapped[list["BmsTelemetryRecord"]] = relationship(back_populates="bms_unit")
    metric_snapshot: Mapped["BmsMetricSnapshot | None"] = relationship(
        back_populates="bms_unit",
        uselist=False,
    )
    incidents: Mapped[list["Incident"]] = relationship(back_populates="bms_unit")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="bms_unit")
    service_record: Mapped["ServiceRecord | None"] = relationship(
        back_populates="bms_unit",
        uselist=False,
    )


class ServiceRecord(Base):
    __tablename__ = "service_records"

    bms_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bms_units.id", ondelete="CASCADE"),
        primary_key=True,
    )
    last_service_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    bms_unit: Mapped["BmsUnit"] = relationship(back_populates="service_record")
