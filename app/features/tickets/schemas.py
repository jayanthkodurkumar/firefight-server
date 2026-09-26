from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.features.tickets.models import TicketStatus


class TicketUnitSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unit_id: str
    site_id: str
    site_name: str | None = None


class TicketRuleSummary(BaseModel):
    id: str
    name: str | None = None


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


class TicketListResponse(BaseModel):
    items: list[TicketListItem]
    total: int
    limit: int
    offset: int
