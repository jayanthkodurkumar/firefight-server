import json

from langchain.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.tickets.evaluator import MERGE_POLICY_ID
from app.features.tickets.models import TicketPolicy


def dump_json(data) -> str:
    return json.dumps(data, default=str)


def build_policy_tools(db: Session) -> list:
    @tool
    def get_policy_rule(rule_id: str) -> str:
        """One row from ticket_policy by id."""
        row = db.get(TicketPolicy, rule_id)
        if not row:
            return dump_json({"error": "rule not found"})
        return dump_json(
            {
                "id": row.id,
                "name": row.name,
                "enabled": row.enabled,
                "definition": row.definition,
            }
        )

    @tool
    def get_policy_rules(rule_ids: list[str]) -> str:
        """Several ticket_policy rows by id."""
        if not rule_ids:
            return dump_json([])
        rows = db.scalars(select(TicketPolicy).where(TicketPolicy.id.in_(rule_ids)))
        return dump_json(
            [
                {"id": r.id, "name": r.name, "enabled": r.enabled, "definition": r.definition}
                for r in rows
            ]
        )

    @tool
    def get_ticket_policy_merge_settings() -> str:
        """ticket_policy merge row (_merge)."""
        row = db.get(TicketPolicy, MERGE_POLICY_ID)
        if not row:
            return dump_json({"error": "merge row not found"})
        return dump_json(row.definition)

    return [get_policy_rule, get_policy_rules, get_ticket_policy_merge_settings]
