"""Import all ORM models so Alembic can target Base.metadata."""

from app.core.db.base import Base
from app.features.bms.models import BmsUnit, ServiceRecord
from app.features.incidents.models import Incident, IncidentEvent
from app.features.rules.models import AlertRule
from app.features.technicians.models import Technician
from app.features.telemetry.models import BmsMetricSnapshot, BmsTelemetryRecord
from app.features.chat.models import ChatMessage, ChatThread
from app.features.tickets.models import Ticket, TicketEvalState, TicketPolicy
from app.features.users.models import User

__all__ = [
    "Base",
    "AlertRule",
    "BmsMetricSnapshot",
    "BmsTelemetryRecord",
    "ChatMessage",
    "ChatThread",
    "BmsUnit",
    "Incident",
    "IncidentEvent",
    "ServiceRecord",
    "Technician",
    "Ticket",
    "TicketEvalState",
    "TicketPolicy",
    "User",
]
