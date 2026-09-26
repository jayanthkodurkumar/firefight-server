"""BMS telemetry record helpers (matches bms_json_logs/telemetry_record.schema.json)."""

from datetime import datetime, timezone
from typing import Any

META_FIELDS = frozenset({"unit", "site", "ts", "t_s"})


def build_record_id(*, unit: str, site: str, recorded_at: datetime) -> str:
    ts = _ensure_aware(recorded_at).isoformat().replace("+00:00", "Z")
    return f"{unit}:{site}:{ts}"


def split_signals(raw: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in raw.items() if key not in META_FIELDS}


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
