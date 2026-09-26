# ruff: noqa: E501

ENTRIES: list[dict] = [
    {"code": "GRD-001", "cat": "GRD", "title": "Grid loss", "detect": "Grid V < 0.5 pu", "reaction": "Open transfer switch; island in ~50 ms", "sev": 0, "dispatch": "out", "recovery": "auto", "inject": "grid = down", "demo": True},
    {"code": "GRD-002", "cat": "GRD", "title": "Undervoltage (UV1)", "detect": "V < 0.88 pu for 2 s", "reaction": "Cease to energize grid; island", "sev": 1, "dispatch": "out", "recovery": "auto", "inject": "grid_v = 0.85", "demo": False},
    {"code": "GRD-003", "cat": "GRD", "title": "Overvoltage (OV1)", "detect": "V > 1.10 pu for 2 s", "reaction": "Trip", "sev": 1, "dispatch": "out", "recovery": "auto", "inject": "grid_v = 1.12", "demo": False},
    {"code": "GRD-004", "cat": "GRD", "title": "Overvoltage (OV2)", "detect": "V > 1.20 pu for 160 ms", "reaction": "Trip", "sev": 1, "dispatch": "out", "recovery": "auto", "inject": "grid_v = 1.22", "demo": False},
    {"code": "GRD-005", "cat": "GRD", "title": "Underfrequency", "detect": "f < 58.5 Hz for 300 s, < 56.5 Hz for 160 ms", "reaction": "Ride through, then trip", "sev": 1, "dispatch": "out", "recovery": "auto", "inject": "grid_f = 58.3", "demo": False},
    {"code": "GRD-006", "cat": "GRD", "title": "Overfrequency", "detect": "f > 61.2 Hz for 300 s, > 62 Hz for 160 ms", "reaction": "Ride through, then trip", "sev": 1, "dispatch": "out", "recovery": "auto", "inject": "grid_f = 61.4", "demo": False},
    {"code": "GRD-007", "cat": "GRD", "title": "Unintentional island", "detect": "Active anti-islanding detects island", "reaction": "Cease export within 2 s", "sev": 3, "dispatch": "out", "recovery": "auto", "inject": "grid = island_feeder", "demo": False},
    {"code": "GRD-008", "cat": "GRD", "title": "ROCOF high", "detect": "df/dt > 0.5 Hz/s", "reaction": "Ride through per profile; log", "sev": 1, "dispatch": "full", "recovery": "auto", "inject": "grid_rocof = 1.0", "demo": False},
    {"code": "GRD-009", "cat": "GRD", "title": "Phase angle jump", "detect": "Vector shift > 20°", "reaction": "Resync", "sev": 1, "dispatch": "full", "recovery": "auto", "inject": "phase_jump = 30", "demo": False},
    {"code": "GRD-010", "cat": "GRD", "title": "Grid return, reconnect delay", "detect": "Grid in range, waiting 300 s enter-service delay", "reaction": "Stay islanded, then sync", "sev": 0, "dispatch": "out", "recovery": "auto", "inject": "grid = up", "demo": False},
    {"code": "GRD-011", "cat": "GRD", "title": "Resync failure", "detect": "Can't match phase/frequency within 60 s", "reaction": "Stay islanded; retry", "sev": 2, "dispatch": "out", "recovery": "retry", "inject": "grid_f_jitter = 0.4", "demo": False},
    {"code": "GRD-012", "cat": "GRD", "title": "Split-phase imbalance", "detect": "|V_L1N − V_L2N| > 5%", "reaction": "Warn; derate", "sev": 2, "dispatch": "derated", "recovery": "auto", "inject": "v_l1 = 1.06; v_l2 = 0.94", "demo": False},
    {"code": "GRD-013", "cat": "GRD", "title": "Open neutral", "detect": "Large opposite L1/L2 swings tracking load", "reaction": "Stop; alert (appliance damage risk)", "sev": 4, "dispatch": "out", "recovery": "truck", "inject": "neutral = open", "demo": False},
    {"code": "GRD-014", "cat": "GRD", "title": "Export limit exceeded", "detect": "Export > interconnection limit", "reaction": "Curtail export", "sev": 1, "dispatch": "derated", "recovery": "auto", "inject": "cmd_export = 1.2*limit", "demo": False},
    {"code": "GRD-015", "cat": "GRD", "title": "Utility remote disable", "detect": "Utility/DR disable signal received", "reaction": "Cease export", "sev": 0, "dispatch": "out", "recovery": "remote", "inject": "utility_disable = True", "demo": False},
]
