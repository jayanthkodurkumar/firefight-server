import json
import uuid

from langchain.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.technicians.models import Technician
from app.features.tickets.models import TicketStatus
from app.features.tickets.repository import get_ticket_by_ticket_id

# ticket.skill (from rules) → technician skills.specialties
SKILL_TO_SPECIALTIES: dict[str, list[str]] = {
    "thermal": ["thermal_diagnostics"],
    "electrical": ["inverter_repair", "bms_firmware", "grid_interconnection"],
    "comms": ["bms_firmware"],
}


def dump_json(data) -> str:
    return json.dumps(data, default=str)


def build_allocation_tools(db: Session, ticket_id: str) -> list:
    @tool
    def list_eligible_technicians() -> str:
        """List technicians who may be assigned to this ticket (region/skill heuristic)."""
        ticket = get_ticket_by_ticket_id(db, ticket_id)
        if not ticket:
            return dump_json({"error": "ticket not found"})
        rows = list(db.scalars(select(Technician).limit(50)))
        want = SKILL_TO_SPECIALTIES.get((ticket.skill or "").lower(), [])
        eligible = []
        for tech in rows:
            skills = tech.skills or {}
            specialties = skills.get("specialties") or []
            if want and not any(s in specialties for s in want):
                continue
            eligible.append(
                {
                    "id": str(tech.id),
                    "name": tech.name,
                    "region": tech.region,
                    "on_call": skills.get("on_call"),
                    "specialties": specialties,
                }
            )
        if not eligible and rows:
            eligible = [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "region": t.region,
                    "on_call": (t.skills or {}).get("on_call"),
                    "specialties": (t.skills or {}).get("specialties"),
                }
                for t in rows[:10]
            ]
        return dump_json(
            {
                "ticket_id": ticket.ticket_id,
                "site_id": ticket.bms_unit.site_id,
                "skill": ticket.skill,
                "technicians": eligible[:15],
            }
        )

    @tool
    def propose_assignment(technician_id: str, notes: str) -> str:
        """Propose assigning a technician (requires human approval before DB write)."""
        try:
            tech_pk = uuid.UUID(technician_id)
        except ValueError:
            return dump_json({"error": "invalid technician_id"})
        tech = db.get(Technician, tech_pk)
        if not tech:
            return dump_json({"error": "technician not found"})
        ticket = get_ticket_by_ticket_id(db, ticket_id)
        if not ticket:
            return dump_json({"error": "ticket not found"})
        if ticket.status == TicketStatus.rejected:
            return dump_json({"error": "ticket was rejected"})
        if ticket.assigned_technician_id is not None or ticket.status == TicketStatus.assigned:
            return dump_json({"error": "ticket already has an assigned technician"})
        return dump_json(
            {
                "action": "assign_technician",
                "ticket_id": ticket.ticket_id,
                "technician_id": str(tech.id),
                "technician_name": tech.name,
                "notes": notes,
            }
        )

    return [list_eligible_technicians, propose_assignment]
