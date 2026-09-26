# ruff: noqa: E501

ENTRIES: list[dict] = [
    {"code": "THM-001", "cat": "THM", "title": "Cell overtemp while charging", "detect": "Cell > 45 °C", "reaction": "Stop charging", "sev": 2, "dispatch": "derated", "recovery": "auto", "inject": "t_cell[j] = 48", "demo": False},
    {"code": "THM-002", "cat": "THM", "title": "Cell overtemp while discharging", "detect": "Cell > 55 °C (derate), > 60 °C (stop)", "reaction": "Derate curve, then stop", "sev": 3, "dispatch": "derated", "recovery": "auto", "inject": "t_cell[j] = 58", "demo": False},
    {"code": "THM-003", "cat": "THM", "title": "Cold charge inhibit", "detect": "Cell < 0 °C", "reaction": "Block charging (Li plating); turn on heater", "sev": 2, "dispatch": "derated", "recovery": "auto", "inject": "ambient = -15", "demo": True},
    {"code": "THM-004", "cat": "THM", "title": "Heater failure", "detect": "< 1 °C rise in 15 min with heater on", "reaction": "Stay charge-inhibited; flag", "sev": 2, "dispatch": "derated", "recovery": "truck", "inject": "heater = dead", "demo": False},
    {"code": "THM-005", "cat": "THM", "title": "Thermal runaway precursor", "detect": "dT/dt > 1 °C/s or off-gas (H2/CO) sensor trips", "reaction": "Open contactors; alert member and ops; fire protocol", "sev": 4, "dispatch": "out", "recovery": "truck", "inject": "offgas = True", "demo": True},
    {"code": "THM-006", "cat": "THM", "title": "Fan / pump failure", "detect": "Tach = 0 while commanded on", "reaction": "Derate power", "sev": 2, "dispatch": "derated", "recovery": "truck", "inject": "fan_rpm = 0", "demo": False},
    {"code": "THM-007", "cat": "THM", "title": "Inverter heatsink overtemp", "detect": "Heatsink > 85 °C", "reaction": "Derate output power", "sev": 2, "dispatch": "derated", "recovery": "auto", "inject": "ambient = 49; p = 11kW", "demo": True},
    {"code": "THM-008", "cat": "THM", "title": "Pack temperature spread", "detect": "Max-min cell temp > 10 °C", "reaction": "Log; check cooling path", "sev": 1, "dispatch": "full", "recovery": "auto", "inject": "t_cell[j] += 12", "demo": False},
    {"code": "THM-009", "cat": "THM", "title": "Ambient out of range", "detect": "Ambient < -30 °C or > 50 °C", "reaction": "Derate", "sev": 2, "dispatch": "derated", "recovery": "auto", "inject": "ambient = 52", "demo": False},
    {"code": "THM-010", "cat": "THM", "title": "Water ingress / humidity", "detect": "Leak or RH sensor trips inside enclosure", "reaction": "Stop", "sev": 3, "dispatch": "out", "recovery": "truck", "inject": "leak = True", "demo": False},
    {"code": "THM-011", "cat": "THM", "title": "Enclosure open / tamper", "detect": "Door switch open while energized", "reaction": "Warn; stop if service not scheduled", "sev": 3, "dispatch": "out", "recovery": "remote", "inject": "door = open", "demo": False},
    {"code": "THM-012", "cat": "THM", "title": "Mechanical impact / tilt", "detect": "Accelerometer shock > 3 g or tilt > 10°", "reaction": "Stop; inspection required (vehicle strike, flood)", "sev": 4, "dispatch": "out", "recovery": "truck", "inject": "accel = 4g", "demo": False},
    {"code": "THM-013", "cat": "THM", "title": "Fire suppression discharged", "detect": "Suppressant pressure switch", "reaction": "Latch", "sev": 4, "dispatch": "out", "recovery": "truck", "inject": "suppressant = fired", "demo": False},
]
