from typing import Any

from app.features.tickets.models import Ticket, TicketStatus


def assignment_pending_action_for_client(
    ticket: Ticket | None,
    pending_action: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if pending_action is None:
        return None
    if pending_action.get("action") != "assign_technician":
        return pending_action
    if ticket is None:
        return pending_action
    if ticket.status in (TicketStatus.assigned, TicketStatus.rejected, TicketStatus.resolved):
        return None
    if ticket.assigned_technician_id is not None:
        return None
    return pending_action
