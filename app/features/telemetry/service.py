from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.batteries.models import Battery
from app.features.telemetry.models import BatteryMetricSnapshot, TelemetryEvent, TelemetryEventKind
from app.features.telemetry.schemas import TelemetryMessage


class TelemetryIngestService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def process_message(self, message: TelemetryMessage) -> bool:
        """
        Persist one telemetry event. Returns True if a new row was inserted,
        False if event_id was already stored (idempotent skip).
        """
        if self._event_exists(message.event_id):
            return False

        battery = self._get_battery_by_external_id(message.battery_id)
        if battery is None:
            raise ValueError(f"Unknown battery_id: {message.battery_id}")

        event_time = _ensure_aware(message.timestamp)
        self._db.add(
            TelemetryEvent(
                event_id=message.event_id,
                battery_pk=battery.id,
                event_time=event_time,
                kind=message.kind,
                payload=message.payload,
            )
        )

        if message.kind == TelemetryEventKind.metric:
            self._upsert_metric_snapshot(
                battery_pk=battery.id,
                event_time=event_time,
                payload=message.payload,
            )

        self._db.flush()
        return True

    def _event_exists(self, event_id: str) -> bool:
        found = self._db.scalar(select(TelemetryEvent.id).where(TelemetryEvent.event_id == event_id))
        return found is not None

    def _get_battery_by_external_id(self, battery_id: str) -> Battery | None:
        return self._db.scalar(select(Battery).where(Battery.battery_id == battery_id))

    def _upsert_metric_snapshot(
        self,
        *,
        battery_pk: Any,
        event_time: datetime,
        payload: dict[str, Any],
    ) -> None:
        snapshot = self._db.get(BatteryMetricSnapshot, battery_pk)
        if snapshot is None:
            snapshot = BatteryMetricSnapshot(battery_pk=battery_pk)
            self._db.add(snapshot)

        snapshot.soc_pct = _optional_float(payload.get("soc_pct"))
        snapshot.temperature_c = _optional_float(payload.get("temperature_c"))
        snapshot.inverter_status = _optional_str(payload.get("inverter_status"))
        snapshot.grid_status = _optional_str(payload.get("grid_status"))
        if "backup_available" in payload:
            snapshot.backup_available = bool(payload["backup_available"])
        snapshot.connectivity = _optional_str(payload.get("connectivity"))
        snapshot.fault_code = _optional_str(payload.get("fault_code"))
        snapshot.last_event_at = event_time


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
