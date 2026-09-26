from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.bms.models import BmsUnit
from app.features.telemetry.models import BmsMetricSnapshot, BmsTelemetryRecord
from app.features.telemetry.record import build_record_id
from app.features.telemetry.schemas import BmsTelemetryRecordMessage


class BmsTelemetryIngestService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def ingest(self, message: BmsTelemetryRecordMessage) -> tuple[bool, uuid.UUID | None, uuid.UUID | None]:
        """Returns (inserted, bms_pk, telemetry_record_pk)."""
        record_id = build_record_id(
            unit=message.unit,
            site=message.site,
            recorded_at=message.ts,
        )
        if self._record_exists(record_id):
            return False, None, None

        bms = self._resolve_or_register_bms(message)
        recorded_at = _ensure_aware(message.ts)
        signals = message.signals()
        row = BmsTelemetryRecord(
            record_id=record_id,
            bms_pk=bms.id,
            unit_id=message.unit,
            site_id=message.site,
            recorded_at=recorded_at,
            t_s=message.t_s,
            signals=signals,
        )
        self._db.add(row)
        self._upsert_snapshot(bms_pk=bms.id, recorded_at=recorded_at, signals=signals)
        self._db.flush()
        return True, bms.id, row.id

    def process_message(self, message: BmsTelemetryRecordMessage) -> bool:
        inserted, _, _ = self.ingest(message)
        return inserted

    def _resolve_or_register_bms(self, message: BmsTelemetryRecordMessage) -> BmsUnit:
        """Match by unit/site; align or create row so ingest works after a table wipe."""
        exact = self._db.scalar(
            select(BmsUnit).where(
                BmsUnit.unit_id == message.unit,
                BmsUnit.site_id == message.site,
            )
        )
        if exact is not None:
            return exact

        by_unit = self._db.scalar(select(BmsUnit).where(BmsUnit.unit_id == message.unit))
        if by_unit is not None:
            if by_unit.site_id != message.site:
                conflict = self._db.scalar(
                    select(BmsUnit.id).where(
                        BmsUnit.site_id == message.site,
                        BmsUnit.id != by_unit.id,
                    )
                )
                if conflict is None:
                    by_unit.site_id = message.site
                    by_unit.site_name = message.site
            return by_unit

        by_site = self._db.scalar(select(BmsUnit).where(BmsUnit.site_id == message.site))
        if by_site is not None:
            return by_site

        row = BmsUnit(
            unit_id=message.unit,
            site_id=message.site,
            site_name=message.site,
            extra={"source": "telemetry_ingest"},
        )
        self._db.add(row)
        self._db.flush()
        return row

    def _record_exists(self, record_id: str) -> bool:
        found = self._db.scalar(
            select(BmsTelemetryRecord.id).where(BmsTelemetryRecord.record_id == record_id)
        )
        return found is not None

    def _upsert_snapshot(
        self,
        *,
        bms_pk: Any,
        recorded_at: datetime,
        signals: dict[str, Any],
    ) -> None:
        snapshot = self._db.get(BmsMetricSnapshot, bms_pk)
        if snapshot is None:
            snapshot = BmsMetricSnapshot(bms_pk=bms_pk)
            self._db.add(snapshot)

        snapshot.soc_pct = _optional_float(signals.get("SOC"))
        snapshot.pack_voltage_v = _optional_float(signals.get("PackVoltage"))
        snapshot.pack_current_a = _optional_float(signals.get("PackCurrent"))
        snapshot.tcell_max_c = _optional_float(signals.get("TcellMax"))
        snapshot.bms_state = _optional_str(signals.get("BmsState"))
        snapshot.hub_mode = _optional_str(signals.get("HubMode"))
        snapshot.fault_bits = _optional_int(signals.get("FaultBits"))
        snapshot.last_record_at = recorded_at


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
