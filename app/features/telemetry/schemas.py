from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BmsTelemetryRecordMessage(BaseModel):
    """
    One JSON Lines telemetry record (see bms_json_logs/telemetry_record.schema.json).
    Signal fields are accepted as extra keys on the same object.
    """

    model_config = ConfigDict(extra="allow")

    unit: str = Field(min_length=1, max_length=16)
    site: str = Field(min_length=1, max_length=64)
    ts: datetime
    t_s: int | None = None

    @field_validator("ts", mode="before")
    @classmethod
    def parse_ts(cls, value: Any) -> Any:
        if isinstance(value, str) and value.endswith("Z"):
            return value.replace("Z", "+00:00")
        return value

    def signals(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        return {
            key: value
            for key, value in data.items()
            if key not in ("unit", "site", "ts", "t_s")
        }
