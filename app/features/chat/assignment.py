import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.features.technicians.models import Technician
from app.features.tickets.models import Ticket, TicketStatus
from app.features.tickets.repository import get_ticket_by_ticket_id


def assign_technician_to_ticket(
    db: Session,
    *,
    ticket_id: str,
    technician_id: uuid.UUID,
    assigned_by_user_id: uuid.UUID,
    notes: str | None,
) -> Ticket:
    ticket = get_ticket_by_ticket_id(db, ticket_id)
    if ticket is None:
        raise ValueError(f"Ticket {ticket_id!r} not found")
    if ticket.status == TicketStatus.rejected:
        raise ValueError("Ticket was rejected")
    if ticket.status == TicketStatus.resolved:
        raise ValueError("Cannot assign a resolved ticket")
    if ticket.assigned_technician_id is not None or ticket.status == TicketStatus.assigned:
        raise ValueError("Ticket already assigned")
    tech = db.get(Technician, technician_id)
    if tech is None:
        raise ValueError("Technician not found")
    ticket.assigned_technician_id = tech.id
    ticket.assigned_by_user_id = assigned_by_user_id
    ticket.dispatch_notes = notes
    ticket.assigned_at = datetime.now(timezone.utc)
    ticket.status = TicketStatus.assigned
    db.commit()
    db.refresh(ticket)
    return ticket


def reject_ticket(
    db: Session,
    *,
    ticket_id: str,
    rejected_by_user_id: uuid.UUID,
    reason: str | None,
) -> Ticket:
    ticket = get_ticket_by_ticket_id(db, ticket_id)
    if ticket is None:
        raise ValueError(f"Ticket {ticket_id!r} not found")
    if ticket.status == TicketStatus.assigned or ticket.assigned_technician_id is not None:
        raise ValueError("Cannot reject an assigned ticket")
    if ticket.status == TicketStatus.rejected:
        raise ValueError("Ticket already rejected")
    if ticket.status == TicketStatus.resolved:
        raise ValueError("Cannot reject a resolved ticket")
    ticket.status = TicketStatus.rejected
    ticket.rejected_by_user_id = rejected_by_user_id
    ticket.rejected_at = datetime.now(timezone.utc)
    ticket.rejection_reason = reason
    db.commit()
    db.refresh(ticket)
    return ticket
