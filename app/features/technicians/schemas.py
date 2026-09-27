from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.features.tickets.models import TicketStatus
from app.features.tickets.schemas import TicketUnitSummary

TechnicianCaseSet = Literal["active", "past", "all"]


class TechnicianListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    region: str | None = None
    employee_id: str | None = None
    on_call: bool | None = None
    specialties: list[str] = []


class TechnicianListResponse(BaseModel):
    items: list[TechnicianListItem]
    total: int


class TechnicianProfile(BaseModel):
    id: str
    name: str
    region: str | None = None
    employee_id: str | None = None
    state: str | None = None
    level: str | None = None
    years_experience: int | None = None
    home_hub: str | None = None
    phone: str | None = None
    on_call: bool | None = None
    specialties: list[str] = []
    certifications: list[str] = []
    active_ticket_count: int
    past_ticket_count: int
    created_at: datetime


class TechnicianTicketSummary(BaseModel):
    ticket_id: str
    status: TicketStatus
    severity: str
    priority: str
    category: str | None
    skill: str | None
    dtc: str | None
    primary_rule_id: str | None
    primary_rule_name: str | None = None
    unit: TicketUnitSummary
    assigned_at: datetime | None
    recorded_at: datetime
    created_at: datetime


class TechnicianTicketsResponse(BaseModel):
    technician_id: str
    case_set: TechnicianCaseSet
    active: list[TechnicianTicketSummary] = Field(default_factory=list)
    past: list[TechnicianTicketSummary] = Field(default_factory=list)
    active_total: int = 0
    past_total: int = 0
    active_limit: int = 50
    active_offset: int = 0
    past_limit: int = 50
    past_offset: int = 0
