import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.features.technicians.models import Technician
from app.features.tickets.models import Ticket, TicketStatus


def list_technicians(db: Session, *, limit: int = 500) -> tuple[list[Technician], int]:
    total = db.scalar(select(func.count()).select_from(Technician)) or 0
    rows = list(
        db.scalars(select(Technician).order_by(Technician.name).limit(limit))
    )
    return rows, total


def get_technician_by_id(db: Session, technician_id: uuid.UUID) -> Technician | None:
    return db.get(Technician, technician_id)


def count_technician_tickets(
    db: Session,
    technician_id: uuid.UUID,
    *,
    status: TicketStatus,
) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(
                Ticket.assigned_technician_id == technician_id,
                Ticket.status == status,
            )
        )
        or 0
    )


def list_technician_tickets(
    db: Session,
    technician_id: uuid.UUID,
    *,
    status: TicketStatus,
    limit: int,
    offset: int,
) -> tuple[list[Ticket], int]:
    base = (
        select(Ticket)
        .where(
            Ticket.assigned_technician_id == technician_id,
            Ticket.status == status,
        )
        .options(
            joinedload(Ticket.bms_unit),
            joinedload(Ticket.telemetry_record),
        )
    )
    count_q = (
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.assigned_technician_id == technician_id,
            Ticket.status == status,
        )
    )
    total = db.scalar(count_q) or 0
    order = Ticket.assigned_at.desc().nullslast(), Ticket.created_at.desc()
    rows = list(db.scalars(base.order_by(*order).limit(limit).offset(offset)))
    return rows, total
