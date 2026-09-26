# ruff: noqa: E501

ENTRIES: list[dict] = [
    {"code": "INS-001", "cat": "INS", "title": "CT polarity reversed", "detect": "Load reads negative at commissioning", "reaction": "Block commissioning", "sev": 3, "dispatch": "out", "recovery": "truck", "inject": "ct_sign = -1", "demo": False},
    {"code": "INS-002", "cat": "INS", "title": "CT on wrong phase", "detect": "Power factor implausible (< 0.3) on one leg", "reaction": "Block commissioning", "sev": 3, "dispatch": "out", "recovery": "truck", "inject": "ct_phase = swapped", "demo": False},
    {"code": "INS-003", "cat": "INS", "title": "Grid profile unset", "detect": "No utility profile selected", "reaction": "No export allowed", "sev": 3, "dispatch": "out", "recovery": "remote", "inject": "grid_profile = None", "demo": False},
    {"code": "INS-004", "cat": "INS", "title": "Double neutral-ground bond", "detect": "Neutral current on ground path", "reaction": "Stop; fix wiring", "sev": 4, "dispatch": "out", "recovery": "truck", "inject": "ng_bond = double", "demo": False},
    {"code": "INS-005", "cat": "INS", "title": "Transfer test not run", "detect": "Commissioning checklist incomplete", "reaction": "No dispatch until test passes", "sev": 2, "dispatch": "out", "recovery": "truck", "inject": "ats_test = pending", "demo": False},
    {"code": "INS-006", "cat": "INS", "title": "Asset not registered", "detect": "Serial not tied to a site in cloud", "reaction": "No dispatch", "sev": 1, "dispatch": "out", "recovery": "remote", "inject": "site_id = None", "demo": False},
    {"code": "INS-007", "cat": "INS", "title": "L1/L2 swapped", "detect": "Measured phase rotation ≠ expected", "reaction": "Block commissioning", "sev": 3, "dispatch": "out", "recovery": "truck", "inject": "phase_swap = True", "demo": False},
    {"code": "INS-008", "cat": "INS", "title": "Undeclared PV", "detect": "PV production seen but not configured", "reaction": "Limit export; request config", "sev": 1, "dispatch": "derated", "recovery": "remote", "inject": "pv_detected = True", "demo": False},
]
