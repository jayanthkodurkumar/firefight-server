import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db.session import get_db
from app.features.auth.dependencies import get_current_user
from app.features.chat.assignment import assign_technician_to_ticket, reject_ticket
from app.features.chat.pending_action_display import assignment_pending_action_for_client
from app.features.chat.repository import clear_assignment_pending_actions, get_thread, list_messages
from app.features.chat.schemas import (
    ApproveAssignmentRequest,
    ApproveAssignmentResponse,
    RejectTicketRequest,
    RejectTicketResponse,
    ChatHistoryItem,
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
)
from app.features.chat.service import run_chat_turn
from app.features.technicians.models import Technician
from app.features.tickets.repository import get_ticket_by_ticket_id
from app.features.users.models import User

router = APIRouter(
    prefix="/api/tickets",
    tags=["chat"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/{ticket_id}/chat/messages", response_model=ChatHistoryResponse)
def get_chat_history(
    ticket_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatHistoryResponse:
    ticket = get_ticket_by_ticket_id(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id!r} not found")
    thread = get_thread(db, user.id, ticket_id)
    if thread is None:
        return ChatHistoryResponse(ticket_id=ticket_id, items=[])
    rows = list_messages(db, thread.id)
    items = [
        ChatHistoryItem(
            id=str(row.id),
            role=row.role,
            content=row.content,
            pending_action=assignment_pending_action_for_client(ticket, row.pending_action),
            created_at=row.created_at,
        )
        for row in rows
    ]
    return ChatHistoryResponse(ticket_id=ticket_id, items=items)


@router.post("/{ticket_id}/chat/messages", response_model=ChatMessageResponse)
def post_chat_message(
    ticket_id: str,
    body: ChatMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatMessageResponse:
    ticket = get_ticket_by_ticket_id(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id!r} not found")
    try:
        reply, pending = run_chat_turn(db, user.id, ticket_id, body.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ChatMessageResponse(
        reply=reply,
        pending_action=assignment_pending_action_for_client(ticket, pending),
    )


@router.post("/{ticket_id}/chat/approve-assignment", response_model=ApproveAssignmentResponse)
def post_approve_assignment(
    ticket_id: str,
    body: ApproveAssignmentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApproveAssignmentResponse:
    if get_ticket_by_ticket_id(db, ticket_id) is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id!r} not found")
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    thread = get_thread(db, user.id, ticket_id)
    if thread is not None:
        clear_assignment_pending_actions(db, thread.id)
    tech = db.get(Technician, ticket.assigned_technician_id)
    return ApproveAssignmentResponse(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        technician_id=str(ticket.assigned_technician_id),
        technician_name=tech.name if tech else None,
    )


@router.post("/{ticket_id}/chat/reject-ticket", response_model=RejectTicketResponse)
def post_reject_ticket(
    ticket_id: str,
    body: RejectTicketRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RejectTicketResponse:
    if get_ticket_by_ticket_id(db, ticket_id) is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id!r} not found")
    try:
        ticket = reject_ticket(
            db,
            ticket_id=ticket_id,
            rejected_by_user_id=user.id,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    thread = get_thread(db, user.id, ticket_id)
    if thread is not None:
        clear_assignment_pending_actions(db, thread.id)
    return RejectTicketResponse(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        rejection_reason=ticket.rejection_reason,
    )
