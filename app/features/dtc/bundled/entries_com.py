# ruff: noqa: E501

ENTRIES: list[dict] = [
    {"code": "COM-001", "cat": "COM", "title": "Cloud heartbeat lost", "detect": "No cloud ack > 60 s", "reaction": "Local autonomous mode: backup first, no export", "sev": 1, "dispatch": "out", "recovery": "auto", "inject": "cloud_link = down", "demo": True},
    {"code": "COM-002", "cat": "COM", "title": "Weak cellular signal", "detect": "RSSI < -105 dBm", "reaction": "Log; prefer Wi-Fi", "sev": 0, "dispatch": "full", "recovery": "auto", "inject": "rssi = -110", "demo": False},
    {"code": "COM-003", "cat": "COM", "title": "All uplinks down", "detect": "LTE and Wi-Fi both down", "reaction": "Buffer telemetry locally", "sev": 1, "dispatch": "out", "recovery": "auto", "inject": "uplinks = none", "demo": False},
    {"code": "COM-004", "cat": "COM", "title": "Frozen telemetry", "detect": "Values unchanged beyond noise for 10 min while running", "reaction": "Mark device suspect; exclude from dispatch", "sev": 2, "dispatch": "out", "recovery": "remote", "inject": "telemetry = freeze", "demo": True},
    {"code": "COM-005", "cat": "COM", "title": "Clock drift", "detect": "|device − NTP| > 2 s", "reaction": "Reject time-critical commands; resync", "sev": 1, "dispatch": "derated", "recovery": "auto", "inject": "clock_skew = 5s", "demo": True},
    {"code": "COM-006", "cat": "COM", "title": "Duplicate command", "detect": "Sequence number already applied", "reaction": "Ignore; re-ack", "sev": 0, "dispatch": "full", "recovery": "auto", "inject": "resend cmd seq=n", "demo": True},
    {"code": "COM-007", "cat": "COM", "title": "Out-of-order command", "detect": "Seq older than last applied", "reaction": "Reject", "sev": 0, "dispatch": "full", "recovery": "auto", "inject": "deliver seq=n-1 after n", "demo": False},
    {"code": "COM-008", "cat": "COM", "title": "Expired command", "detect": "Arrives after its TTL", "reaction": "Reject; report", "sev": 0, "dispatch": "full", "recovery": "auto", "inject": "net_delay = 30s", "demo": True},
    {"code": "COM-009", "cat": "COM", "title": "Internal CAN bus-off", "detect": "CAN controller bus-off", "reaction": "Stop; auto-recover 128x11 bits", "sev": 3, "dispatch": "out", "recovery": "auto", "inject": "can = bus_off", "demo": False},
    {"code": "COM-010", "cat": "COM", "title": "Internal message timeout", "detect": "Cyclic frame missing > 3 periods", "reaction": "Stop", "sev": 3, "dispatch": "out", "recovery": "auto", "inject": "drop msg INV_STATUS", "demo": False},
    {"code": "COM-011", "cat": "COM", "title": "E2E check failed", "detect": "CRC or alive-counter error on safety frame", "reaction": "Discard frame; stop after 3", "sev": 3, "dispatch": "out", "recovery": "auto", "inject": "corrupt crc", "demo": False},
    {"code": "COM-012", "cat": "COM", "title": "Auth / certificate failure", "detect": "TLS handshake fails, cert expired", "reaction": "Cloud link down; rotate cert", "sev": 1, "dispatch": "out", "recovery": "remote", "inject": "cert = expired", "demo": False},
    {"code": "COM-013", "cat": "COM", "title": "Telemetry backpressure", "detect": "Upload queue > 80% full", "reaction": "Drop low-priority telemetry first", "sev": 1, "dispatch": "full", "recovery": "auto", "inject": "uplink_bw = 1kbps", "demo": False},
]
