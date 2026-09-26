# ruff: noqa: E501

ENTRIES: list[dict] = [
    {"code": "SWF-001", "cat": "SWF", "title": "Firmware set incompatible", "detect": "BMS/INV/HUB versions not in compatibility matrix", "reaction": "Backup-only mode", "sev": 3, "dispatch": "out", "recovery": "remote", "inject": "fw_bms = old", "demo": False},
    {"code": "SWF-002", "cat": "SWF", "title": "OTA image invalid", "detect": "Hash or signature check fails", "reaction": "Discard; stay on current", "sev": 0, "dispatch": "full", "recovery": "auto", "inject": "ota_blob = corrupt", "demo": False},
    {"code": "SWF-003", "cat": "SWF", "title": "OTA install failed", "detect": "New partition fails health check", "reaction": "Roll back to previous A/B slot", "sev": 1, "dispatch": "full", "recovery": "auto", "inject": "ota_boot = fail", "demo": False},
    {"code": "SWF-004", "cat": "SWF", "title": "Boot loop", "detect": "> 3 resets in 10 min", "reaction": "Safe mode", "sev": 3, "dispatch": "out", "recovery": "remote", "inject": "crash_on_boot = True", "demo": False},
    {"code": "SWF-005", "cat": "SWF", "title": "Main controller watchdog", "detect": "Watchdog reset", "reaction": "Log; restart", "sev": 1, "dispatch": "full", "recovery": "auto", "inject": "hang_main = True", "demo": False},
    {"code": "SWF-006", "cat": "SWF", "title": "Wrong grid profile", "detect": "Configured 1547 settings ≠ utility/site record", "reaction": "Block export", "sev": 3, "dispatch": "out", "recovery": "remote", "inject": "grid_profile = wrong", "demo": False},
    {"code": "SWF-007", "cat": "SWF", "title": "Log storage full", "detect": "Storage > 95%", "reaction": "Rotate logs", "sev": 1, "dispatch": "full", "recovery": "auto", "inject": "disk = 0.97", "demo": False},
    {"code": "SWF-008", "cat": "SWF", "title": "Control loop overrun", "detect": "Deadline misses > 1% of cycles", "reaction": "Derate", "sev": 2, "dispatch": "derated", "recovery": "remote", "inject": "cpu_load = 1.2", "demo": False},
    {"code": "SWF-009", "cat": "SWF", "title": "Schedule violates limits", "detect": "Dispatch plan breaks SOC or power limits", "reaction": "Clamp; report back to cloud", "sev": 1, "dispatch": "derated", "recovery": "auto", "inject": "plan_soc_min = 0", "demo": False},
    {"code": "SWF-010", "cat": "SWF", "title": "Secure boot failure", "detect": "Bootloader signature check fails", "reaction": "Refuse to boot application", "sev": 4, "dispatch": "out", "recovery": "truck", "inject": "fw_sig = bad", "demo": False},
    {"code": "SWF-011", "cat": "SWF", "title": "Setpoint out of range", "detect": "Cloud command > rated or NaN", "reaction": "Reject", "sev": 0, "dispatch": "full", "recovery": "auto", "inject": "cmd_kw = NaN", "demo": False},
]
