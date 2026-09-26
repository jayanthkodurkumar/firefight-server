from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db.session import get_db
from app.features.tickets.models import TicketStatus
from app.features.tickets.repository import get_policy_names, get_ticket_by_ticket_id, list_tickets
from app.features.tickets.schemas import (
    TicketDetail,
    TicketListItem,
    TicketListResponse,
    TicketRuleSummary,
    TicketUnitSummary,
)

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


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
    )
