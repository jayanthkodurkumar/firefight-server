from app.features.technicians.models import Technician
from app.features.technicians.schemas import (
    TechnicianListItem,
    TechnicianProfile,
    TechnicianTicketSummary,
)
from app.features.tickets.models import Ticket
from app.features.tickets.schemas import TicketUnitSummary


def technician_list_item(tech: Technician) -> TechnicianListItem:
    skills = tech.skills or {}
    specialties = skills.get("specialties") or []
    on_call = skills.get("on_call")
    employee_id = skills.get("employee_id")
    return TechnicianListItem(
        id=str(tech.id),
        name=tech.name,
        region=tech.region,
        employee_id=employee_id if isinstance(employee_id, str) else None,
        on_call=on_call if isinstance(on_call, bool) else None,
        specialties=list(specialties) if isinstance(specialties, list) else [],
    )


def technician_profile(
    tech: Technician,
    *,
    active_ticket_count: int,
    past_ticket_count: int,
) -> TechnicianProfile:
    skills = tech.skills or {}
    specialties = skills.get("specialties") or []
    certifications = skills.get("certifications") or []
    on_call = skills.get("on_call")
    return TechnicianProfile(
        id=str(tech.id),
        name=tech.name,
        region=tech.region,
        employee_id=skills.get("employee_id") if isinstance(skills.get("employee_id"), str) else None,
        state=skills.get("state") if isinstance(skills.get("state"), str) else None,
        level=skills.get("level") if isinstance(skills.get("level"), str) else None,
        years_experience=skills.get("years_experience")
        if isinstance(skills.get("years_experience"), int)
        else None,
        home_hub=skills.get("home_hub") if isinstance(skills.get("home_hub"), str) else None,
        phone=skills.get("phone") if isinstance(skills.get("phone"), str) else None,
        on_call=on_call if isinstance(on_call, bool) else None,
        specialties=list(specialties) if isinstance(specialties, list) else [],
        certifications=list(certifications) if isinstance(certifications, list) else [],
        active_ticket_count=active_ticket_count,
        past_ticket_count=past_ticket_count,
        created_at=tech.created_at,
    )


def technician_ticket_summary(ticket: Ticket, primary_rule_name: str | None) -> TechnicianTicketSummary:
    unit = ticket.bms_unit
    return TechnicianTicketSummary(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        severity=ticket.severity,
        priority=ticket.priority,
        category=ticket.category,
        skill=ticket.skill,
        dtc=ticket.dtc,
        primary_rule_id=ticket.primary_rule_id,
        primary_rule_name=primary_rule_name,
        unit=TicketUnitSummary(
            unit_id=unit.unit_id,
            site_id=unit.site_id,
            site_name=unit.site_name,
        ),
        assigned_at=ticket.assigned_at,
        recorded_at=ticket.recorded_at,
        created_at=ticket.created_at,
    )
