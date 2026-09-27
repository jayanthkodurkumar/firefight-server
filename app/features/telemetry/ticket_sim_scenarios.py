"""Signal bursts for publish sim — one primary rule per scenario (evaluator-supported types)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TicketSimScenario:
    rule_id: str
    samples: int
    patch: dict[str, Any]


def _base() -> dict[str, Any]:
    """Nominal values so other rules stay quiet."""
    return {
        "ContactorPosCmd": 1,
        "ContactorPosFb": 1,
        "ContactorNegCmd": 1,
        "ContactorNegFb": 1,
        "BusVoltage": 408.0,
        "OffGasH2": 0.0,
        "TcellMax": 32.0,
        "TcellMin": 28.0,
        "IsolationRes": 4800,
        "State_CrcOk": True,
        "PackStatus_CrcOk": True,
        "BmsState": "DISCHARGE",
        "CurrentHall": 14.0,
        "CurrentShunt": 14.0,
        "FanCmd": 30,
        "FanRpm": 1200,
    }


TICKET_SIM_SCENARIOS: list[TicketSimScenario] = [
    TicketSimScenario(
        rule_id="R-ELE-01",
        samples=1,
        patch={**_base(), "ContactorPosCmd": 0, "ContactorNegCmd": 0, "ContactorPosFb": 1, "BusVoltage": 395.0},
    ),
    TicketSimScenario(
        rule_id="R-THM-02",
        samples=2,
        patch={**_base(), "OffGasH2": 150.0, "BmsState": "FAULT"},
    ),
    TicketSimScenario(
        rule_id="R-ELE-02",
        samples=2,
        patch={
            **_base(),
            "ContactorPosCmd": 0,
            "ContactorPosFb": 0,
            "ContactorNegCmd": 0,
            "ContactorNegFb": 0,
            "BusVoltage": 390.0,
        },
    ),
    TicketSimScenario(
        rule_id="R-THM-03",
        samples=10,
        patch={**_base(), "TcellMax": 58.0, "TcellMin": 52.0},
    ),
    TicketSimScenario(
        rule_id="R-ELE-03",
        samples=10,
        patch={**_base(), "IsolationRes": 150},
    ),
    TicketSimScenario(
        rule_id="R-COM-02",
        samples=3,
        patch={**_base(), "State_CrcOk": False},
    ),
    TicketSimScenario(
        rule_id="R-COM-03",
        samples=6,
        patch={**_base(), "State_AliveCounter": 7, "PackStatus_AliveCounter": 7},
    ),
    TicketSimScenario(
        rule_id="R-SEN-01",
        samples=30,
        patch={**_base(), "CurrentHall": 20.0, "CurrentShunt": 14.0, "PackCurrent": 14.0},
    ),
    TicketSimScenario(
        rule_id="R-MEC-01",
        samples=30,
        patch={**_base(), "FanCmd": 85, "FanRpm": 150},
    ),
]

# Default publish rotation (≤3 samples). Order matters for demo variety.
_PUBLISH_ORDER = ("R-THM-02", "R-ELE-02", "R-COM-02", "R-ELE-01")
_by_rule_id = {s.rule_id: s for s in TICKET_SIM_SCENARIOS}
TICKET_SIM_SCENARIOS_PUBLISH: list[TicketSimScenario] = [
    _by_rule_id[rid] for rid in _PUBLISH_ORDER
]

# Full set including long for_s (10–30 sample bursts).
TICKET_SIM_SCENARIOS_LONG: list[TicketSimScenario] = [
    s for s in TICKET_SIM_SCENARIOS if s.samples > 3
]
