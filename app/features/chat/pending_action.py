import json
from typing import Any

from langchain.messages import AnyMessage, ToolMessage


def find_pending_action(messages: list[AnyMessage]) -> dict[str, Any] | None:
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            continue
        try:
            data = json.loads(msg.content)
        except (json.JSONDecodeError, TypeError):
            continue
        if data.get("action") == "assign_technician" and data.get("technician_id"):
            return data
    return None
