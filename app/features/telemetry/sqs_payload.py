"""SQS message body: JSON telemetry envelope (see bms_json_logs/telemetry_record.schema.json)."""

import json
from typing import Any

FORMAT = "bms_telemetry_record"


def build_message_body(record: dict[str, Any]) -> str:
    """Serialize one telemetry record for SQS MessageBody (UTF-8 JSON string)."""
    envelope = {
        "format": FORMAT,
        "record": record,
    }
    return json.dumps(envelope, separators=(",", ":"), ensure_ascii=False)


def parse_message_body(raw: str) -> dict[str, Any]:
    """
    Parse SQS MessageBody into the flat telemetry record dict.
    Supports: JSON envelope, bare record, or SNS-wrapped JSON.
    """
    data = json.loads(raw)

    if isinstance(data, dict) and data.get("Type") == "Notification" and "Message" in data:
        data = json.loads(data["Message"])

    if isinstance(data, dict) and data.get("format") == FORMAT and "record" in data:
        record = data["record"]
        if not isinstance(record, dict):
            raise ValueError("envelope record must be a JSON object")
        return record

    if isinstance(data, dict) and "unit" in data and "site" in data and "ts" in data:
        return data

    raise ValueError("unsupported message body: expected bms_telemetry_record JSON")
