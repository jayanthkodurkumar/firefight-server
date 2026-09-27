from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.features.chat.models import ChatMessageRole
from app.features.tickets.models import TicketStatus


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class ChatMessageResponse(BaseModel):
    reply: str
    pending_action: dict | None = None


class ChatHistoryItem(BaseModel):
    id: str
    role: ChatMessageRole
    content: str
    pending_action: dict[str, Any] | None = None
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    ticket_id: str
    items: list[ChatHistoryItem]


class ApproveAssignmentRequest(BaseModel):
    technician_id: str
    notes: str | None = None


class ApproveAssignmentResponse(BaseModel):
    ticket_id: str
    status: TicketStatus
    technician_id: str
    technician_name: str | None = None


class RejectTicketRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class RejectTicketResponse(BaseModel):
    ticket_id: str
    status: TicketStatus
    rejection_reason: str | None = None
