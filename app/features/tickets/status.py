import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy.orm import Session

from app.features.tickets.models import Ticket, TicketStatus
from app.features.tickets.repository import get_ticket_by_ticket_id

PatchableTicketStatus = Literal[TicketStatus.rejected, TicketStatus.resolved]


def patch_ticket_status(
    db: Session,
    *,
    ticket_id: str,
    status: PatchableTicketStatus,
    actor_user_id: uuid.UUID,
    reason: str | None = None,
) -> Ticket:
    ticket = get_ticket_by_ticket_id(db, ticket_id)
    if ticket is None:
        raise ValueError(f"Ticket {ticket_id!r} not found")

    if status == TicketStatus.rejected:
        if ticket.status == TicketStatus.rejected:
            raise ValueError("Ticket already rejected")
        if ticket.status == TicketStatus.resolved:
            raise ValueError("Cannot reject a resolved ticket")
        if ticket.status == TicketStatus.assigned or ticket.assigned_technician_id is not None:
            raise ValueError("Cannot reject an assigned ticket")
        ticket.status = TicketStatus.rejected
        ticket.rejected_by_user_id = actor_user_id
        ticket.rejected_at = datetime.now(timezone.utc)
        ticket.rejection_reason = reason
    elif status == TicketStatus.resolved:
        if ticket.status == TicketStatus.resolved:
            raise ValueError("Ticket already resolved")
        ticket.status = TicketStatus.resolved
    else:
        raise ValueError("Unsupported status")

    db.commit()
    db.refresh(ticket)
    return ticket
