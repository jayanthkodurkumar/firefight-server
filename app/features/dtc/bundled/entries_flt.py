# ruff: noqa: E501

ENTRIES: list[dict] = [
    {"code": "FLT-001", "cat": "FLT", "title": "Device not acking", "detect": "No ack after 3 retries", "reaction": "Mark unavailable; reassign its share", "sev": 2, "dispatch": "out", "recovery": "auto", "inject": "kill device", "demo": True},
    {"code": "FLT-002", "cat": "FLT", "title": "Tracking error", "detect": "Delivered vs committed MW off > 10% over interval", "reaction": "Redistribute; alert", "sev": 2, "dispatch": "derated", "recovery": "auto", "inject": "derate 20% of fleet", "demo": True},
    {"code": "FLT-003", "cat": "FLT", "title": "Committed capacity at risk", "detect": "Available MW < obligation + margin", "reaction": "Alert trading; buy back position", "sev": 2, "dispatch": "derated", "recovery": "remote", "inject": "kill 30% fleet", "demo": False},
    {"code": "FLT-004", "cat": "FLT", "title": "Dispatcher leader lost", "detect": "Leader lease expired", "reaction": "Standby takes over", "sev": 1, "dispatch": "full", "recovery": "auto", "inject": "kill dispatcher", "demo": True},
    {"code": "FLT-005", "cat": "FLT", "title": "Stale leader (split brain)", "detect": "Command carries old fencing token", "reaction": "Devices reject it", "sev": 1, "dispatch": "full", "recovery": "auto", "inject": "pause+resume old leader", "demo": True},
    {"code": "FLT-006", "cat": "FLT", "title": "Market data stale", "detect": "ERCOT price feed > 2 intervals late", "reaction": "Hold last plan; be conservative", "sev": 1, "dispatch": "derated", "recovery": "auto", "inject": "price_feed = stall", "demo": True},
    {"code": "FLT-007", "cat": "FLT", "title": "Telemetry ingestion lag", "detect": "Pipeline lag > 30 s", "reaction": "Widen safety margins", "sev": 1, "dispatch": "derated", "recovery": "auto", "inject": "ingest_delay = 45s", "demo": False},
    {"code": "FLT-008", "cat": "FLT", "title": "Correlated dropout", "detect": "> 20% of devices on one feeder drop at once", "reaction": "Classify as grid outage, not device fault", "sev": 0, "dispatch": "out", "recovery": "auto", "inject": "outage feeder F12", "demo": True},
    {"code": "FLT-009", "cat": "FLT", "title": "Storm reserve raise", "detect": "Severe weather forecast for region", "reaction": "Raise backup reserve fleet-wide", "sev": 0, "dispatch": "derated", "recovery": "auto", "inject": "storm zone=Houston", "demo": False},
    {"code": "FLT-010", "cat": "FLT", "title": "Reconnect storm", "detect": "Mass reconnect after regional outage", "reaction": "Jittered backoff", "sev": 1, "dispatch": "derated", "recovery": "auto", "inject": "restore feeder F12", "demo": False},
    {"code": "FLT-011", "cat": "FLT", "title": "Settlement mismatch", "detect": "Revenue meter vs telemetry differ > 2%", "reaction": "Flag for reconciliation", "sev": 1, "dispatch": "full", "recovery": "remote", "inject": "meter_bias = 0.03", "demo": False},
    {"code": "FLT-012", "cat": "FLT", "title": "Bad firmware cohort", "detect": "Fault rate on new version > 2x baseline", "reaction": "Halt rollout; roll back cohort", "sev": 2, "dispatch": "derated", "recovery": "remote", "inject": "fw_v2 fault_rate x3", "demo": True},
]
