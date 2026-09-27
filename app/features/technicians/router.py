import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db.session import get_db
from app.features.auth.dependencies import get_current_user
from app.features.technicians.repository import (
    count_technician_tickets,
    get_technician_by_id,
    list_technician_tickets,
    list_technicians,
)
from app.features.technicians.schemas import (
    TechnicianCaseSet,
    TechnicianListResponse,
    TechnicianProfile,
    TechnicianTicketsResponse,
)
from app.features.technicians.serialization import (
    technician_list_item,
    technician_profile,
    technician_ticket_summary,
)
from app.features.tickets.models import TicketStatus
from app.features.tickets.repository import get_policy_names

router = APIRouter(
    prefix="/api/technicians",
    tags=["technicians"],
    dependencies=[Depends(get_current_user)],
)


def parse_technician_id(technician_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(technician_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid technician_id")


def load_technician(db: Session, technician_id: str):
    tech = get_technician_by_id(db, parse_technician_id(technician_id))
    if tech is None:
        raise HTTPException(status_code=404, detail=f"Technician {technician_id!r} not found")
    return tech


def tickets_to_summaries(db: Session, rows: list) -> list:
    rule_ids = [t.primary_rule_id for t in rows if t.primary_rule_id]
    names = get_policy_names(db, rule_ids)
    return [
        technician_ticket_summary(
            t,
            names.get(t.primary_rule_id) if t.primary_rule_id else None,
        )
        for t in rows
    ]


@router.get("", response_model=TechnicianListResponse)
def get_technicians(
    db: Session = Depends(get_db),
    limit: int = Query(500, ge=1, le=500),
) -> TechnicianListResponse:
    rows, total = list_technicians(db, limit=limit)
    return TechnicianListResponse(
        items=[technician_list_item(tech) for tech in rows],
        total=total,
    )


@router.get("/{technician_id}", response_model=TechnicianProfile)
def get_technician(technician_id: str, db: Session = Depends(get_db)) -> TechnicianProfile:
    tech = load_technician(db, technician_id)
    tech_pk = tech.id
    active_count = count_technician_tickets(db, tech_pk, status=TicketStatus.assigned)
    past_count = count_technician_tickets(db, tech_pk, status=TicketStatus.resolved)
    return technician_profile(
        tech,
        active_ticket_count=active_count,
        past_ticket_count=past_count,
    )


@router.get("/{technician_id}/tickets", response_model=TechnicianTicketsResponse)
def get_technician_tickets(
    technician_id: str,
    db: Session = Depends(get_db),
    case_set: TechnicianCaseSet = Query("all"),
    active_limit: int = Query(50, ge=1, le=200),
    active_offset: int = Query(0, ge=0),
    past_limit: int = Query(50, ge=1, le=200),
    past_offset: int = Query(0, ge=0),
) -> TechnicianTicketsResponse:
    tech = load_technician(db, technician_id)
    tech_pk = tech.id

    active_rows: list = []
    past_rows: list = []
    active_total = 0
    past_total = 0

    if case_set in ("active", "all"):
        active_rows, active_total = list_technician_tickets(
            db,
            tech_pk,
            status=TicketStatus.assigned,
            limit=active_limit,
            offset=active_offset,
        )
    if case_set in ("past", "all"):
        past_rows, past_total = list_technician_tickets(
            db,
            tech_pk,
            status=TicketStatus.resolved,
            limit=past_limit,
            offset=past_offset,
        )

    return TechnicianTicketsResponse(
        technician_id=str(tech_pk),
        case_set=case_set,
        active=tickets_to_summaries(db, active_rows),
        past=tickets_to_summaries(db, past_rows),
        active_total=active_total if case_set in ("active", "all") else 0,
        past_total=past_total if case_set in ("past", "all") else 0,
        active_limit=active_limit,
        active_offset=active_offset,
        past_limit=past_limit,
        past_offset=past_offset,
    )
