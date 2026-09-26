"""Load BMS fleet catalog from bms_json_logs/out/examples/units.json."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_UNITS_CATALOG = REPO_ROOT / "bms_json_logs" / "out" / "examples" / "units.json"
DEFAULT_JSON_LOGS_DIR = REPO_ROOT / "bms_json_logs" / "out" / "examples" / "json_logs"
TELEMETRY_SCHEMA_PATH = REPO_ROOT / "bms_json_logs" / "telemetry_record.schema.json"


def load_units_catalog(path: Path | None = None) -> list[dict]:
    catalog_path = path or DEFAULT_UNITS_CATALOG
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def resolve_json_log_path(unit_row: dict, *, logs_root: Path | None = None) -> Path:
    root = logs_root or DEFAULT_JSON_LOGS_DIR
    rel = unit_row.get("json_log") or ""
    name = Path(rel).name
    if not name:
        unit = unit_row["unit"]
        site = unit_row["site"]
        name = f"{unit}_{site}.jsonl"
    candidate = root / name
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"JSON log not found: {candidate}")
