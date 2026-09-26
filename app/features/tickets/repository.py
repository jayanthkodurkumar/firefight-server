from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.features.bms.models import BmsUnit
from app.features.tickets.models import Ticket, TicketPolicy, TicketStatus


def list_tickets(
    db: Session,
    *,
    limit: int,
    offset: int,
    status: TicketStatus | None = None,
) -> tuple[list[Ticket], int]:
    base = select(Ticket).join(Ticket.bms_unit).options(
        joinedload(Ticket.bms_unit),
        joinedload(Ticket.telemetry_record),
    )
    count_q = select(func.count()).select_from(Ticket)

    if status is not None:
        base = base.where(Ticket.status == status)
        count_q = count_q.where(Ticket.status == status)

    total = db.scalar(count_q) or 0
    rows = list(
        db.scalars(
            base.order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
        )
    )
    return rows, total


def get_ticket_by_ticket_id(db: Session, ticket_id: str) -> Ticket | None:
    return db.scalar(
        select(Ticket)
        .where(Ticket.ticket_id == ticket_id)
        .options(
            joinedload(Ticket.bms_unit),
            joinedload(Ticket.primary_rule),
            joinedload(Ticket.telemetry_record),
        )
    )


def get_policy_names(db: Session, rule_ids: list[str]) -> dict[str, str | None]:
    if not rule_ids:
        return {}
    rows = db.scalars(select(TicketPolicy).where(TicketPolicy.id.in_(rule_ids)))
    return {row.id: row.name or (row.definition or {}).get("name") for row in rows}
