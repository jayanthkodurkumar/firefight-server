import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base

if TYPE_CHECKING:
    from app.features.incidents.models import Incident
    from app.features.telemetry.models import BatteryMetricSnapshot, TelemetryEvent


class Battery(Base):
    __tablename__ = "batteries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    battery_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    site_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    telemetry_events: Mapped[list["TelemetryEvent"]] = relationship(back_populates="battery")
    metric_snapshot: Mapped["BatteryMetricSnapshot | None"] = relationship(
        back_populates="battery",
        uselist=False,
    )
    incidents: Mapped[list["Incident"]] = relationship(back_populates="battery")
    service_record: Mapped["ServiceRecord | None"] = relationship(
        back_populates="battery",
        uselist=False,
    )


class ServiceRecord(Base):
    __tablename__ = "service_records"

    battery_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batteries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    last_service_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    battery: Mapped["Battery"] = relationship(back_populates="service_record")
