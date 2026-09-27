from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.features.tickets.models import TicketStatus

PatchTicketStatus = Literal[TicketStatus.rejected, TicketStatus.resolved]


class TicketUnitSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unit_id: str
    site_id: str
    site_name: str | None = None


class TicketRuleSummary(BaseModel):
    id: str
    name: str | None = None


class TicketAssignedTo(BaseModel):
    id: str
    name: str | None = None


class TicketAssignedBy(BaseModel):
    id: str
    email: str | None = None


class TicketListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: str
    status: TicketStatus
    severity: str
    priority: str
    category: str | None
    skill: str | None
    dtc: str | None
    primary_rule_id: str | None
    primary_rule_name: str | None = None
    record_id: str | None = None
    unit: TicketUnitSummary
    recorded_at: datetime
    created_at: datetime
    assigned_to: TicketAssignedTo | None = None
    assigned_by: TicketAssignedBy | None = None
    assigned_at: datetime | None = None


class TicketDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_id: str
    status: TicketStatus
    severity: str
    priority: str
    category: str | None
    skill: str | None
    dtc: str | None
    hint: str | None
    primary_rule_id: str | None
    primary_rule: TicketRuleSummary | None = None
    fired_rules: list[str]
    fired_rule_details: list[TicketRuleSummary] = Field(default_factory=list)
    unit: TicketUnitSummary
    telemetry_record_pk: UUID
    record_id: str
    state_snapshot: dict[str, Any]
    recorded_at: datetime
    created_at: datetime
    assigned_to: TicketAssignedTo | None = None
    assigned_by: TicketAssignedBy | None = None
    assigned_at: datetime | None = None
    dispatch_notes: str | None = None


class TicketListResponse(BaseModel):
    items: list[TicketListItem]
    total: int
    limit: int
    offset: int


class PatchTicketRequest(BaseModel):
    status: PatchTicketStatus
    reason: str | None = Field(default=None, max_length=2000)


class PatchTicketResponse(BaseModel):
    ticket_id: str
    status: TicketStatus
    rejection_reason: str | None = None


class AssignTicketRequest(BaseModel):
    technician_id: str
    notes: str | None = Field(default=None, max_length=2000)


class AssignTicketResponse(BaseModel):
    ticket_id: str
    status: TicketStatus
    technician_id: str
    technician_name: str | None = None
    dispatch_notes: str | None = None
