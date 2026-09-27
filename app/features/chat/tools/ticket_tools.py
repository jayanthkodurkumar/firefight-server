import json

from langchain.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.tickets.models import TicketPolicy
from app.features.tickets.repository import get_policy_names, get_ticket_by_ticket_id


def dump_json(data) -> str:
    return json.dumps(data, default=str)


def build_ticket_tools(db: Session, ticket_id: str) -> list:
    @tool
    def get_ticket_summary() -> str:
        """Ticket header: status, severity, unit, primary rule, fired rules, hint (no snapshot)."""
        ticket = get_ticket_by_ticket_id(db, ticket_id)
        if not ticket:
            return dump_json({"error": "ticket not found"})
        unit = ticket.bms_unit
        fired = list(ticket.fired_rules or [])
        names = get_policy_names(db, fired)
        primary = ticket.primary_rule
        primary_name = primary.name if primary and primary.name else None
        if primary and not primary_name:
            primary_name = (primary.definition or {}).get("name")
        return dump_json(
            {
                "ticket_id": ticket.ticket_id,
                "status": ticket.status.value,
                "severity": ticket.severity,
                "priority": ticket.priority,
                "category": ticket.category,
                "skill": ticket.skill,
                "dtc": ticket.dtc,
                "hint": ticket.hint,
                "recorded_at": ticket.recorded_at,
                "unit_id": unit.unit_id,
                "site_id": unit.site_id,
                "site_name": unit.site_name,
                "primary_rule_id": ticket.primary_rule_id,
                "primary_rule_name": primary_name,
                "fired_rules": [{"id": r, "name": names.get(r)} for r in fired],
            }
        )

    @tool
    def get_ticket_signals_at_open(signal_names: list[str] | None = None) -> str:
        """Values from state_snapshot when the ticket opened."""
        ticket = get_ticket_by_ticket_id(db, ticket_id)
        if not ticket:
            return dump_json({"error": "ticket not found"})
        snap = ticket.state_snapshot or {}
        if signal_names:
            snap = {k: snap.get(k) for k in signal_names}
        return dump_json({"recorded_at": ticket.recorded_at, "signals": snap})

    @tool
    def get_ticket_firing_context() -> str:
        """Why opened: hint, rules, and snapshot (use get_policy_rules for full rule JSON)."""
        ticket = get_ticket_by_ticket_id(db, ticket_id)
        if not ticket:
            return dump_json({"error": "ticket not found"})
        fired = list(ticket.fired_rules or [])
        rows = list(db.scalars(select(TicketPolicy).where(TicketPolicy.id.in_(fired)))) if fired else []
        return dump_json(
            {
                "primary_rule_id": ticket.primary_rule_id,
                "fired_rule_ids": fired,
                "hint": ticket.hint,
                "severity": ticket.severity,
                "priority": ticket.priority,
                "state_snapshot": ticket.state_snapshot,
                "policies": [
                    {"id": r.id, "name": r.name, "definition": r.definition} for r in rows
                ],
            }
        )

    return [get_ticket_summary, get_ticket_signals_at_open, get_ticket_firing_context]
