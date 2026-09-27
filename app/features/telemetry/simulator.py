"""Synthetic BMS telemetry: nominal fleet behavior + rare spontaneous fault episodes."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class _Episode:
    kind: str
    remaining: int
    intensity: float = 1.0


@dataclass
class _UnitState:
    rng: random.Random
    t_s: int = 0
    soc: float = 65.0
    pack_voltage: float = 408.0
    pack_current: float = 14.0
    tcell_max: float = 30.0
    offgas_h2: float = 0.0
    isolation_kohm: float = 4800.0
    humidity: float = 40.0
    vcell_max: float = 3.18
    vcell_min: float = 3.14
    alive: int = 0
    alive_frozen: bool = False
    contactor_cmd: int = 1
    contactor_fb: int = 1
    hall_bias: float = 0.0
    shunt_bias: float = 0.0
    crc_fail_streak: int = 0
    state_crc_ok: bool = True
    pack_crc_ok: bool = True
    episode: _Episode | None = None
    episode_started_kind: str | None = None
    cooldown: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # per-unit hazard multiplier (some units are slightly more trouble-prone)
    hazard: float = 1.0


# Spontaneous episode types (same stream as healthy data — no manual injection).
_EPISODE_PLANS: dict[str, tuple[int, int]] = {
    "thermal_runup": (30, 70),
    "cell_overtemp": (15, 35),
    "venting": (10, 25),
    "isolation_leak": (50, 100),
    "contactor_weld": (12, 30),
    "sensor_drift": (40, 90),
    "comms_crc": (8, 18),
    "fw_alive_stuck": (10, 25),
}

# Bias toward episodes that move telemetry into fault bands within ~10–30 samples.
_EPISODE_WEIGHTS: list[str] = (
    ["thermal_runup", "cell_overtemp", "venting", "contactor_weld", "comms_crc"] * 3
    + ["fw_alive_stuck", "sensor_drift", "isolation_leak"]
)


class BmsTelemetrySimulator:
    """
    Per-unit 1 Hz state. Faults start rarely on their own, evolve over many samples,
    then clear (or leave the unit degraded). Matches how real telemetry arrives.
    """

    def __init__(self, *, seed: int = 7, hazard_scale: float = 1.0, enable_episodes: bool = True) -> None:
        self._seed = seed
        self._hazard_scale = hazard_scale
        self._enable_episodes = enable_episodes
        self._units: dict[tuple[str, str], _UnitState] = {}

    def _state(self, unit: str, site: str) -> _UnitState:
        key = (unit, site)
        if key not in self._units:
            unit_seed = hash((self._seed, unit, site)) & 0xFFFFFFFF
            rng = random.Random(unit_seed)
            st = _UnitState(
                rng=rng,
                soc=55.0 + (unit_seed % 300) / 10.0,
                pack_voltage=400.0 + (unit_seed % 200) / 10.0,
                pack_current=10.0 + (unit_seed % 80) / 10.0,
                tcell_max=26.0 + (unit_seed % 60) / 10.0,
                isolation_kohm=4200.0 + (unit_seed % 800),
                hazard=0.7 + (unit_seed % 100) / 200.0,
            )
            self._units[key] = st
        return self._units[key]

    def _maybe_start_episode(self, st: _UnitState) -> None:
        if st.episode is not None or st.cooldown > 0:
            return
        # ~0.5% per simulated second per unit → several fleet episodes per few minutes.
        p = 0.005 * self._hazard_scale * st.hazard
        if st.rng.random() >= p:
            return
        kind = st.rng.choice(_EPISODE_WEIGHTS)
        lo, hi = _EPISODE_PLANS[kind]
        duration = st.rng.randint(lo, hi)
        st.episode = _Episode(kind=kind, remaining=duration, intensity=st.rng.uniform(0.9, 1.3))
        st.episode_started_kind = kind
        if kind == "fw_alive_stuck":
            st.alive_frozen = True
        if kind == "contactor_weld":
            st.contactor_cmd = 0
            st.contactor_fb = 1

    def _step_episode(self, st: _UnitState) -> None:
        ep = st.episode
        if ep is None:
            return

        k = ep.kind
        i = ep.intensity

        if k in ("thermal_runup", "cell_overtemp"):
            st.tcell_max += st.rng.uniform(0.25, 0.65) * i
            st.pack_current = min(45.0, st.pack_current + st.rng.uniform(0, 0.8))
            if st.tcell_max > 50 and k == "thermal_runup":
                st.offgas_h2 = max(st.offgas_h2, st.rng.uniform(30, 120) * (st.tcell_max - 48) / 10)

        elif k == "venting":
            st.offgas_h2 = min(250.0, st.offgas_h2 + st.rng.uniform(25, 70) * i)
            st.tcell_max += st.rng.uniform(0.15, 0.45)

        elif k == "isolation_leak":
            st.isolation_kohm = max(80.0, st.isolation_kohm - st.rng.uniform(35, 90) * i)
            st.humidity = min(85.0, st.humidity + st.rng.uniform(0, 0.15))

        elif k == "contactor_weld":
            st.contactor_cmd = 0
            st.contactor_fb = 1
            # bus stays near pack — service hazard if rule checks after open

        elif k == "sensor_drift":
            st.hall_bias += st.rng.uniform(-0.25, 0.25) * i
            st.shunt_bias += st.rng.uniform(-0.05, 0.05)

        elif k == "comms_crc":
            if st.rng.random() < 0.72 * i:
                st.state_crc_ok = False
                st.crc_fail_streak += 1
            else:
                st.state_crc_ok = True

        elif k == "fw_alive_stuck":
            pass  # alive counter handled in next_record

        ep.remaining -= 1
        if ep.remaining <= 0:
            st.episode = None
            st.cooldown = st.rng.randint(45, 180)
            if k == "fw_alive_stuck":
                st.alive_frozen = False
            if k == "contactor_weld":
                st.contactor_cmd = 1
                st.contactor_fb = 1
            st.state_crc_ok = True
            st.crc_fail_streak = 0

    def _step_nominal(self, st: _UnitState) -> None:
        if st.cooldown > 0:
            st.cooldown -= 1

        st.soc = max(10.0, min(98.0, st.soc + st.rng.uniform(-0.05, 0.05)))
        if st.episode is None:
            st.pack_current = max(-5.0, min(40.0, st.pack_current + st.rng.uniform(-0.3, 0.3)))
            st.tcell_max = max(24.0, min(54.0, st.tcell_max + st.rng.uniform(-0.06, 0.08)))
            st.offgas_h2 = max(0.0, st.offgas_h2 - st.rng.uniform(0, 2))
            if st.isolation_kohm < 4000:
                st.isolation_kohm = min(5500.0, st.isolation_kohm + st.rng.uniform(0, 5))
            else:
                st.isolation_kohm = max(3500.0, min(5500.0, st.isolation_kohm + st.rng.uniform(-3, 3)))
            st.hall_bias *= 0.995
            st.shunt_bias *= 0.995
        st.pack_voltage = 320.0 + st.soc * 1.2 + st.rng.uniform(-0.5, 0.5)

        st.vcell_max = max(2.9, min(3.55, 3.15 + (st.soc - 50) * 0.004 + st.rng.uniform(-0.02, 0.04)))
        st.vcell_min = max(2.75, st.vcell_max - st.rng.uniform(0.03, 0.08))

    def next_record(self, unit: str, site: str) -> dict:
        st = self._state(unit, site)
        st.t_s += 1

        if not st.alive_frozen:
            st.alive = (st.alive + 1) % 16
        # else counter repeats → alive_stuck rule

        if self._enable_episodes:
            self._maybe_start_episode(st)
            self._step_episode(st)
        self._step_nominal(st)

        ts = st.started_at + timedelta(seconds=st.t_s)
        ts_str = ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

        pack_i = round(st.pack_current, 1)
        hall = round(pack_i + st.hall_bias, 1)
        shunt = round(pack_i + st.shunt_bias + st.rng.uniform(-0.15, 0.15), 1)
        bms_state = "DISCHARGE" if st.pack_current > 1 else "STANDBY"
        if st.episode and st.episode.kind in ("thermal_runup", "venting", "cell_overtemp") and st.tcell_max > 54:
            bms_state = "FAULT"

        if st.contactor_cmd == 0 and st.contactor_fb == 1:
            bus_v = round(st.pack_voltage, 1)
        elif st.contactor_fb == 0:
            bus_v = round(max(0.0, st.rng.uniform(0, 20)), 1)
        else:
            bus_v = round(st.pack_voltage, 1)

        record: dict = {
            "unit": unit,
            "site": site,
            "ts": ts_str,
            "t_s": st.t_s,
            "PackVoltage": round(st.pack_voltage, 1),
            "PackCurrent": pack_i,
            "SOC": round(st.soc, 1),
            "SOH": round(96.0 + st.rng.uniform(-1, 1), 1),
            "PackStatus_AliveCounter": st.alive,
            "PackStatus_CRC8": st.rng.randint(0, 255),
            "PackStatus_CrcOk": st.pack_crc_ok,
            "VcellMax": round(st.vcell_max, 3),
            "VcellMin": round(st.vcell_min, 3),
            "VcellMaxId": st.rng.randint(0, 127),
            "VcellMinId": st.rng.randint(0, 127),
            "VcellAvg": round((st.vcell_max + st.vcell_min) / 2, 3),
            "TcellMax": round(st.tcell_max, 1),
            "TcellMin": round(st.tcell_max - st.rng.uniform(1, 4), 1),
            "TcellMaxId": st.rng.randint(0, 15),
            "TcellMinId": st.rng.randint(0, 15),
            "HeaterOn": 0,
            "OffGasH2": round(st.offgas_h2, 1),
            "Humidity": round(st.humidity, 1),
            "ChargeCurrentLimit": 120.0,
            "DischargeCurrentLimit": 120.0,
            "MaxChargeVoltage": 460.8,
            "LimitReason": "NONE",
            "BmsState": bms_state,
            "ContactorPosCmd": st.contactor_cmd,
            "ContactorPosFb": st.contactor_fb,
            "ContactorNegCmd": st.contactor_cmd,
            "ContactorNegFb": st.contactor_fb,
            "PrechargeRelay": 0,
            "BalancingCount": 0,
            "IsolationRes": int(round(st.isolation_kohm)),
            "FaultBits": 0,
            "State_AliveCounter": st.alive,
            "State_CRC8": st.rng.randint(0, 255),
            "State_CrcOk": st.state_crc_ok,
            "AuxSupplyV": round(12.0 + st.rng.uniform(-0.1, 0.15), 2),
            "CurrentHall": hall,
            "CurrentShunt": shunt,
            "BusVoltage": bus_v,
            "AcPower": round(st.pack_voltage * st.pack_current * 0.95, 0),
            "DcLinkV": round(st.pack_voltage, 1),
            "HeatsinkT": round(45 + (st.tcell_max - 28) * 0.8 + st.rng.uniform(0, 4)),
            "FanCmd": st.rng.randint(25, 35),
            "FanRpm": st.rng.randint(1100, 1300),
            "GridPresent": 1,
            "AtsCmdOpen": 0,
            "AtsAuxOpen": 0,
            "AtsVsenseOpen": 0,
            "HubMode": "GRID",
            "GridVoltage": round(238.0 + st.rng.uniform(0, 5), 1),
            "GridFreq": round(59.99 + st.rng.uniform(-0.02, 0.02), 3),
            "CellVoltages": None,
            "CellTemps": None,
        }

        if st.t_s % 10 == 0:
            base = st.vcell_max
            record["CellVoltages"] = [
                round(base + st.rng.uniform(-0.03, 0.03), 3) for _ in range(128)
            ]
            record["CellTemps"] = [
                round(st.tcell_max - st.rng.uniform(0, 3), 1) for _ in range(16)
            ]

        return record
