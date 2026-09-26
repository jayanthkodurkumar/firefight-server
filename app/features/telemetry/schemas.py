from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.features.telemetry.models import TelemetryEventKind


class TelemetryMessage(BaseModel):
    """SQS message body for one telemetry event."""

    event_id: str = Field(min_length=1, max_length=128)
    battery_id: str = Field(min_length=1, max_length=64)
    timestamp: datetime
    kind: TelemetryEventKind
    payload: dict[str, Any] = Field(default_factory=dict)
