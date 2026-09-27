"""Evaluate telemetry records against rows in ticket_policy."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.telemetry.models import BmsTelemetryRecord
from app.features.tickets.models import Ticket, TicketEvalState, TicketPolicy

MERGE_POLICY_ID = "_merge"
SEVERITY_RANK = {"S4": 0, "S3": 1, "S2": 2, "S1": 3}
PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

# DBC "Message.Signal" → telemetry_record.schema.json field name
SIGNAL_FIELDS: dict[str, str] = {
    "BMS_TempSummary.TcellMax": "TcellMax",
    "BMS_TempSummary.OffGasH2": "OffGasH2",
    "BMS_CellSummary.VcellMax": "VcellMax",
    "BMS_CellSummary.VcellMin": "VcellMin",
    "BMS_State.IsolationRes": "IsolationRes",
    "BMS_State.BmsState": "BmsState",
    "BMS_State.ContactorPosCmd": "ContactorPosCmd",
    "BMS_State.ContactorPosFb": "ContactorPosFb",
    "BMS_Aux.CurrentHall": "CurrentHall",
    "BMS_Aux.CurrentShunt": "CurrentShunt",
    "BMS_Aux.BusVoltage": "BusVoltage",
    "INV_Status.HeatsinkT": "HeatsinkT",
    "INV_Status.FanCmd": "FanCmd",
    "INV_Status.FanRpm": "FanRpm",
}


@dataclass(frozen=True, slots=True)
class RuleHit:
    rule_id: str
    name: str
    severity: str
    priority: str
    category: str | None
    skill: str | None
    dtc: str | None
    hint: str | None
    definition: dict[str, Any]


def signal_value(signals: dict[str, Any], dbc_signal: str) -> Any:
    field = SIGNAL_FIELDS.get(dbc_signal)
    if field is None and "." in dbc_signal:
        field = dbc_signal.split(".", 1)[1]
    if field is None:
        return None
    return signals.get(field)


def _compare(op: str, left: float, right: float) -> bool:
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    return False


class TicketPolicyEvaluator:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._rules: list[TicketPolicy] | None = None
        self._merge: dict[str, Any] | None = None

    def _load_policies(self) -> None:
        if self._rules is not None:
            return
        rows = list(
            self._db.scalars(
                select(TicketPolicy)
                .where(TicketPolicy.id != MERGE_POLICY_ID, TicketPolicy.enabled.is_(True))
                .order_by(TicketPolicy.id)
            )
        )
        self._rules = rows
        merge_row = self._db.get(TicketPolicy, MERGE_POLICY_ID)
        self._merge = merge_row.definition if merge_row else {}

    def evaluate(
        self,
        *,
        bms_pk: uuid.UUID,
        signals: dict[str, Any],
        recorded_at: datetime,
        prior_record: BmsTelemetryRecord | None,
    ) -> list[RuleHit]:
        self._load_policies()
        assert self._rules is not None

        hits: list[RuleHit] = []
        for row in self._rules:
            rule = row.definition
            rule_type = rule.get("type") or row.rule_type
            if rule_type == "fleet_outlier":
                continue
            if self._evaluate_rule(
                bms_pk=bms_pk,
                rule_id=row.id,
                rule=rule,
                rule_type=rule_type,
                signals=signals,
                recorded_at=recorded_at,
                prior_record=prior_record,
            ):
                hits.append(
                    RuleHit(
                        rule_id=row.id,
                        name=rule.get("name") or row.name or row.id,
                        severity=str(rule.get("severity", "S2")),
                        priority=str(rule.get("priority", "P3")),
                        category=rule.get("category"),
                        skill=rule.get("skill"),
                        dtc=rule.get("dtc"),
                        hint=rule.get("hint"),
                        definition=rule,
                    )
                )
        return hits

    def _eval_state(self, bms_pk: uuid.UUID, rule_id: str) -> TicketEvalState:
        row = self._db.get(TicketEvalState, (bms_pk, rule_id))
        if row is None:
            row = TicketEvalState(bms_pk=bms_pk, rule_id=rule_id, state={})
            self._db.add(row)
            self._db.flush()
        return row

    def _streak_hit(
        self,
        *,
        bms_pk: uuid.UUID,
        rule_id: str,
        condition: bool,
        required: int,
    ) -> bool:
        st = self._eval_state(bms_pk, rule_id)
        streak = int(st.state.get("streak", 0))
        if condition:
            streak += 1
        else:
            streak = 0
        st.state = {**st.state, "streak": streak}
        return streak >= required

    def _evaluate_rule(
        self,
        *,
        bms_pk: uuid.UUID,
        rule_id: str,
        rule: dict[str, Any],
        rule_type: str | None,
        signals: dict[str, Any],
        recorded_at: datetime,
        prior_record: BmsTelemetryRecord | None,
    ) -> bool:
        for_s = int(rule.get("for_s") or rule.get("for_samples") or 1)

        if rule_type == "threshold":
            raw = signal_value(signals, str(rule["signal"]))
            if raw is None:
                return self._streak_hit(
                    bms_pk=bms_pk, rule_id=rule_id, condition=False, required=for_s
                )
            ok = _compare(str(rule["op"]), float(raw), float(rule["value"]))
            return self._streak_hit(bms_pk=bms_pk, rule_id=rule_id, condition=ok, required=for_s)

        if rule_type == "rate":
            field = SIGNAL_FIELDS.get(str(rule["signal"]), "TcellMax")
            cur = signals.get(field)
            if cur is None or prior_record is None:
                return False
            prev = prior_record.signals.get(field)
            if prev is None:
                return False
            dt = (recorded_at - prior_record.recorded_at).total_seconds()
            if dt <= 0:
                return False
            rate = (float(cur) - float(prev)) / dt
            ok = _compare(str(rule.get("op", ">")), rate, float(rule["value"]))
            return self._streak_hit(bms_pk=bms_pk, rule_id=rule_id, condition=ok, required=for_s)

        if rule_type == "cmd_fb":
            cmd = signal_value(signals, str(rule["cmd"]))
            fb = signal_value(signals, str(rule["fb"]))
            if cmd is None or fb is None:
                return False
            ok = int(cmd) != int(fb)
            return self._streak_hit(bms_pk=bms_pk, rule_id=rule_id, condition=ok, required=for_s)

        if rule_type == "mismatch":
            a = signal_value(signals, str(rule["a"]))
            b = signal_value(signals, str(rule["b"]))
            if a is None or b is None:
                return False
            ok = abs(float(a) - float(b)) > float(rule["value"])
            return self._streak_hit(bms_pk=bms_pk, rule_id=rule_id, condition=ok, required=for_s)

        if rule_type == "bus_after_open":
            fb = signals.get("ContactorPosFb")
            bus = signals.get("BusVoltage")
            if fb is None or bus is None:
                return False
            opened = int(fb) == 0
            live = float(bus) > float(rule["value"])
            return self._streak_hit(
                bms_pk=bms_pk,
                rule_id=rule_id,
                condition=opened and live,
                required=for_s,
            )

        if rule_type == "cmd_fb_analog":
            cmd = signal_value(signals, str(rule["cmd"]))
            fb = signal_value(signals, str(rule["fb"]))
            if cmd is None or fb is None:
                return False
            ok = float(cmd) >= float(rule["cmd_min"]) and float(fb) <= float(rule["fb_max"])
            return self._streak_hit(bms_pk=bms_pk, rule_id=rule_id, condition=ok, required=for_s)

        if rule_type == "crc_errors":
            bad = signals.get("State_CrcOk") is False or signals.get("PackStatus_CrcOk") is False
            min_events = int(rule.get("min_events") or 1)
            return self._streak_hit(bms_pk=bms_pk, rule_id=rule_id, condition=bad, required=min_events)

        if rule_type == "alive_stuck":
            alive = signals.get("State_AliveCounter")
            st = self._eval_state(bms_pk, rule_id)
            last = st.state.get("last_alive")
            same = last is not None and alive is not None and int(last) == int(alive)
            st.state = {**st.state, "last_alive": alive}
            min_rep = int(rule.get("min_repeats") or 5)
            return self._streak_hit(bms_pk=bms_pk, rule_id=rule_id, condition=same, required=min_rep)

        return False


def apply_suppressions(hits: list[RuleHit]) -> list[RuleHit]:
    suppressed: set[str] = set()
    for hit in hits:
        for other in rule.get("suppresses", []) if (rule := hit.definition) else []:
            suppressed.add(str(other))
    return [h for h in hits if h.rule_id not in suppressed]


def pick_primary(hits: list[RuleHit]) -> RuleHit:
    return sorted(
        hits,
        key=lambda h: (SEVERITY_RANK.get(h.severity, 9), PRIORITY_RANK.get(h.priority, 9), h.rule_id),
    )[0]


def adjust_priority(hits: list[RuleHit], signals: dict[str, Any], merge: dict[str, Any]) -> str:
    best = min((PRIORITY_RANK.get(h.priority, 9) for h in hits), default=3)
    priority = {v: k for k, v in PRIORITY_RANK.items()}[best]

    if signals.get("BmsState") == "FAULT":
        if PRIORITY_RANK.get(priority, 9) > PRIORITY_RANK["P1"]:
            priority = "P1"

    for hit in hits:
        if hit.severity == "S4" and hit.category == "thermal":
            return "P0"

    return priority


def new_ticket_id() -> str:
    return f"TKT-{uuid.uuid4().hex[:8].upper()}"


def create_ticket_from_hits(
    db: Session,
    *,
    bms_pk: uuid.UUID,
    telemetry_record_pk: uuid.UUID,
    signals: dict[str, Any],
    recorded_at: datetime,
    hits: list[RuleHit],
    merge: dict[str, Any],
) -> Ticket | None:
    if not hits:
        return None

    eligible = apply_suppressions(hits)
    if not eligible:
        return None

    primary = pick_primary(eligible)
    priority = adjust_priority(eligible, signals, merge)

    existing = db.scalar(
        select(Ticket.id).where(Ticket.telemetry_record_pk == telemetry_record_pk)
    )
    if existing is not None:
        return None

    ticket = Ticket(
        ticket_id=new_ticket_id(),
        bms_pk=bms_pk,
        telemetry_record_pk=telemetry_record_pk,
        primary_rule_id=primary.rule_id,
        fired_rules=[h.rule_id for h in hits],
        severity=primary.severity,
        priority=priority,
        category=primary.category,
        skill=primary.skill,
        dtc=primary.dtc,
        hint=primary.hint,
        state_snapshot=signals,
        recorded_at=_aware(recorded_at),
        assigned_technician_id=None,
        assigned_by_user_id=None,
        dispatch_notes=None,
        assigned_at=None,
    )
    db.add(ticket)
    db.flush()
    return ticket


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
