import uuid

from langchain.messages import AIMessage, AnyMessage, HumanMessage
from sqlalchemy.orm import Session

from app.features.chat.models import ChatMessageRole
from app.features.chat.pending_action_display import assignment_pending_action_for_client
from app.features.tickets.repository import get_ticket_by_ticket_id
from app.features.chat.orchestrator import compile_ticket_chat
from app.features.chat.repository import (
    add_message,
    get_or_create_thread,
    list_messages,
    messages_to_langchain,
)


def last_assistant_reply(messages: list[AnyMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return ""


def run_chat_turn(
    db: Session,
    user_id: uuid.UUID,
    ticket_id: str,
    user_message: str,
) -> tuple[str, dict | None]:
    thread = get_or_create_thread(db, user_id, ticket_id)
    history = messages_to_langchain(list_messages(db, thread.id))
    messages = history + [HumanMessage(content=user_message)]

    app = compile_ticket_chat(db, ticket_id)
    result = app.invoke(
        {
            "ticket_id": ticket_id,
            "messages": messages,
            "route": None,
            "pending_action": None,
        }
    )
    reply = last_assistant_reply(result["messages"])
    pending = result.get("pending_action")
    ticket = get_ticket_by_ticket_id(db, ticket_id)
    pending = assignment_pending_action_for_client(ticket, pending)

    add_message(db, thread, ChatMessageRole.user, user_message)
    add_message(db, thread, ChatMessageRole.assistant, reply, pending_action=pending)
    return reply, pending
