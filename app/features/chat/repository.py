import uuid

from langchain.messages import AIMessage, AnyMessage, HumanMessage
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.chat.models import ChatMessage, ChatMessageRole, ChatThread


def get_thread(db: Session, user_id: uuid.UUID, ticket_id: str) -> ChatThread | None:
    return db.scalar(
        select(ChatThread).where(
            ChatThread.user_id == user_id,
            ChatThread.ticket_id == ticket_id,
        )
    )


def get_or_create_thread(db: Session, user_id: uuid.UUID, ticket_id: str) -> ChatThread:
    thread = get_thread(db, user_id, ticket_id)
    if thread is not None:
        return thread
    thread = ChatThread(user_id=user_id, ticket_id=ticket_id)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


def list_messages(db: Session, thread_id: uuid.UUID) -> list[ChatMessage]:
    return list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.created_at)
        )
    )


def add_message(
    db: Session,
    thread: ChatThread,
    role: ChatMessageRole,
    content: str,
    pending_action: dict | None = None,
) -> ChatMessage:
    row = ChatMessage(
        thread_id=thread.id,
        role=role,
        content=content,
        pending_action=pending_action,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def clear_assignment_pending_actions(db: Session, thread_id: uuid.UUID) -> None:
    rows = list_messages(db, thread_id)
    dirty = False
    for row in rows:
        action = (row.pending_action or {}).get("action")
        if action == "assign_technician":
            row.pending_action = None
            dirty = True
    if dirty:
        db.commit()


def messages_to_langchain(rows: list[ChatMessage]) -> list[AnyMessage]:
    out: list[AnyMessage] = []
    for row in rows:
        if row.role == ChatMessageRole.user:
            out.append(HumanMessage(content=row.content))
        else:
            out.append(AIMessage(content=row.content))
    return out
