"""Import all ORM models so Alembic can target Base.metadata."""

from app.core.db.base import Base
from app.features.batteries.models import Battery, ServiceRecord
from app.features.dtc.models import DtcCatalogMeta, DtcEntry
from app.features.incidents.models import Incident, IncidentEvent
from app.features.rules.models import AlertRule
from app.features.technicians.models import Technician
from app.features.telemetry.models import BatteryMetricSnapshot, TelemetryEvent

__all__ = [
    "Base",
    "AlertRule",
    "Battery",
    "BatteryMetricSnapshot",
    "DtcCatalogMeta",
    "DtcEntry",
    "Incident",
    "IncidentEvent",
    "ServiceRecord",
    "Technician",
    "TelemetryEvent",
]
