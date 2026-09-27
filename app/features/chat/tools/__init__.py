from sqlalchemy.orm import Session

from app.features.chat.tools.policy_tools import build_policy_tools
from app.features.chat.tools.ticket_tools import build_ticket_tools


def build_qa_tools(db: Session, ticket_id: str) -> list:
    return build_ticket_tools(db, ticket_id) + build_policy_tools(db)
