import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db.session import get_db
from app.features.auth.dependencies import get_current_user
from app.features.chat.assignment import assign_technician_to_ticket
from app.features.chat.repository import clear_assignment_pending_actions, get_thread
from app.features.technicians.models import Technician
from app.features.tickets.models import TicketStatus
from app.features.tickets.repository import get_policy_names, get_ticket_by_ticket_id, list_tickets
from app.features.tickets.schemas import (
    AssignTicketRequest,
    AssignTicketResponse,
    PatchTicketRequest,
    PatchTicketResponse,
    TicketAssignedBy,
    TicketAssignedTo,
    TicketDetail,
    TicketListItem,
    TicketListResponse,
    TicketRuleSummary,
    TicketUnitSummary,
)
from app.features.tickets.status import patch_ticket_status
from app.features.users.models import User

router = APIRouter(
    prefix="/api/tickets",
    tags=["tickets"],
    dependencies=[Depends(get_current_user)],
)


def _rule_name(policy: object | None) -> str | None:
    if policy is None:
        return None
    name = getattr(policy, "name", None)
    if name:
        return name
    definition = getattr(policy, "definition", None) or {}
    return definition.get("name")


def _unit_summary(ticket) -> TicketUnitSummary:
    unit = ticket.bms_unit
    return TicketUnitSummary(
        unit_id=unit.unit_id,
        site_id=unit.site_id,
        site_name=unit.site_name,
    )


def _record_id(ticket) -> str | None:
    rec = ticket.telemetry_record
    return rec.record_id if rec is not None else None


def _assigned_to(ticket) -> TicketAssignedTo | None:
    if ticket.assigned_technician_id is None:
        return None
    tech = ticket.assigned_technician
    if tech is not None:
        return TicketAssignedTo(id=str(tech.id), name=tech.name)
    return TicketAssignedTo(id=str(ticket.assigned_technician_id), name=None)


def _email_local_part(email: str) -> str:
    return email.split("@", 1)[0]


def _assigned_by(ticket) -> TicketAssignedBy | None:
    if ticket.assigned_by_user_id is None:
        return None
    user = ticket.assigned_by_user
    if user is not None:
        return TicketAssignedBy(id=str(user.id), email=_email_local_part(user.email))
    return TicketAssignedBy(id=str(ticket.assigned_by_user_id), email=None)


def _to_list_item(ticket, primary_rule_name: str | None) -> TicketListItem:
    return TicketListItem(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        severity=ticket.severity,
        priority=ticket.priority,
        category=ticket.category,
        skill=ticket.skill,
        dtc=ticket.dtc,
        primary_rule_id=ticket.primary_rule_id,
        primary_rule_name=primary_rule_name,
        record_id=_record_id(ticket),
        unit=_unit_summary(ticket),
        recorded_at=ticket.recorded_at,
        created_at=ticket.created_at,
        assigned_to=_assigned_to(ticket),
        assigned_by=_assigned_by(ticket),
        assigned_at=ticket.assigned_at,
    )


@router.get("", response_model=TicketListResponse)
def get_all_tickets(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: TicketStatus | None = None,
) -> TicketListResponse:
    rows, total = list_tickets(db, limit=limit, offset=offset, status=status)
    rule_ids = [t.primary_rule_id for t in rows if t.primary_rule_id]
    names = get_policy_names(db, rule_ids)
    items = [
        _to_list_item(t, names.get(t.primary_rule_id) if t.primary_rule_id else None)
        for t in rows
    ]
    return TicketListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/{ticket_id}/assign", response_model=AssignTicketResponse)
def post_assign_ticket(
    ticket_id: str,
    body: AssignTicketRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssignTicketResponse:
    try:
        tech_pk = uuid.UUID(body.technician_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid technician_id")
    try:
        ticket = assign_technician_to_ticket(
            db,
            ticket_id=ticket_id,
            technician_id=tech_pk,
            assigned_by_user_id=user.id,
            notes=body.notes,
        )
    except ValueError as exc:
        if "not found" in str(exc) and "Ticket" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    thread = get_thread(db, user.id, ticket_id)
    if thread is not None:
        clear_assignment_pending_actions(db, thread.id)
    tech = db.get(Technician, ticket.assigned_technician_id)
    return AssignTicketResponse(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        technician_id=str(ticket.assigned_technician_id),
        technician_name=tech.name if tech else None,
        dispatch_notes=ticket.dispatch_notes,
    )


@router.patch("/{ticket_id}", response_model=PatchTicketResponse)
def patch_ticket(
    ticket_id: str,
    body: PatchTicketRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PatchTicketResponse:
    try:
        ticket = patch_ticket_status(
            db,
            ticket_id=ticket_id,
            status=body.status,
            actor_user_id=user.id,
            reason=body.reason,
        )
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PatchTicketResponse(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        rejection_reason=ticket.rejection_reason,
    )


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)) -> TicketDetail:
    ticket = get_ticket_by_ticket_id(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id!r} not found")

    record_id = _record_id(ticket)
    if record_id is None:
        raise HTTPException(
            status_code=500,
            detail=f"Ticket {ticket_id!r} has no linked telemetry record",
        )

    primary = None
    if ticket.primary_rule is not None:
        primary = TicketRuleSummary(
            id=ticket.primary_rule.id,
            name=_rule_name(ticket.primary_rule),
        )

    fired_ids = list(ticket.fired_rules or [])
    fired_names = get_policy_names(db, fired_ids)
    fired_details = [
        TicketRuleSummary(id=rid, name=fired_names.get(rid)) for rid in fired_ids
    ]

    return TicketDetail(
        id=ticket.id,
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        severity=ticket.severity,
        priority=ticket.priority,
        category=ticket.category,
        skill=ticket.skill,
        dtc=ticket.dtc,
        hint=ticket.hint,
        primary_rule_id=ticket.primary_rule_id,
        primary_rule=primary,
        fired_rules=fired_ids,
        fired_rule_details=fired_details,
        unit=_unit_summary(ticket),
        telemetry_record_pk=ticket.telemetry_record_pk,
        record_id=record_id,
        state_snapshot=ticket.state_snapshot,
        recorded_at=ticket.recorded_at,
        created_at=ticket.created_at,
        assigned_to=_assigned_to(ticket),
        assigned_by=_assigned_by(ticket),
        assigned_at=ticket.assigned_at,
        dispatch_notes=ticket.dispatch_notes,
    )
