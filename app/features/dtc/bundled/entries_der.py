# ruff: noqa: E501

ENTRIES: list[dict] = [
    {"code": "DER-001", "cat": "DER", "title": "Low backup runtime", "detect": "Projected runtime < 4 h during outage", "reaction": "Notify member; suggest shedding big loads", "sev": 1, "dispatch": "out", "recovery": "auto", "inject": "house_load = 9kW; soc = 0.3", "demo": False},
    {"code": "DER-002", "cat": "DER", "title": "Backup energy exhausted", "detect": "SOC < 5% in island", "reaction": "Graceful shutdown; restart on grid or PV", "sev": 3, "dispatch": "out", "recovery": "auto", "inject": "soc = 0.04", "demo": True},
    {"code": "DER-003", "cat": "DER", "title": "PV surplus in island", "detect": "Battery full and PV exporting in island", "reaction": "Frequency shift to curtail PV", "sev": 1, "dispatch": "out", "recovery": "auto", "inject": "pv = 8kW; soc = 1.0", "demo": False},
    {"code": "DER-004", "cat": "DER", "title": "PV not responding to curtailment", "detect": "Island V/f rising despite frequency shift", "reaction": "Disconnect PV branch; stop", "sev": 3, "dispatch": "out", "recovery": "auto", "inject": "pv_freq_watt = off", "demo": False},
    {"code": "DER-005", "cat": "DER", "title": "Generator input out of spec", "detect": "Gen-port V/f unstable", "reaction": "Reject generator", "sev": 1, "dispatch": "out", "recovery": "auto", "inject": "gen_f = 57", "demo": False},
    {"code": "DER-006", "cat": "DER", "title": "Generator overcurrent", "detect": "Gen-port current > rating", "reaction": "Limit charge from generator", "sev": 2, "dispatch": "derated", "recovery": "auto", "inject": "gen_i = 1.3*rated", "demo": False},
    {"code": "DER-007", "cat": "DER", "title": "3rd-party PV comms lost", "detect": "SunSpec/Modbus timeout > 30 s", "reaction": "Assume worst-case PV; conservative island control", "sev": 1, "dispatch": "derated", "recovery": "auto", "inject": "pv_modbus = down", "demo": False},
    {"code": "DER-008", "cat": "DER", "title": "Load-shed relay failure", "detect": "Smart-breaker relay feedback mismatch", "reaction": "Can't shed; lower overload threshold", "sev": 2, "dispatch": "derated", "recovery": "truck", "inject": "shed_relay[k] = stuck", "demo": False},
    {"code": "DER-009", "cat": "DER", "title": "Unexpected base load", "detect": "Standby load > 2x 30-day baseline", "reaction": "Info to member", "sev": 0, "dispatch": "full", "recovery": "auto", "inject": "house_base += 2kW", "demo": False},
]
