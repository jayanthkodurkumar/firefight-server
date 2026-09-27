from typing import Annotated, Literal

from langchain.chat_models import init_chat_model
from langchain.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from sqlalchemy.orm import Session
from typing_extensions import TypedDict

from app.core.config.settings import get_settings
from app.features.chat.allocation_agent import compile_allocation_agent
from app.features.chat.pending_action import find_pending_action
from app.features.chat.qa_agent import compile_qa_agent

Route = Literal["qa", "allocation"]

ROUTER_SYSTEM_PROMPT = (
    "You route messages for a BMS ticket chat. "
    "Reply with exactly one word: qa or allocation.\n"
    "qa — questions about the ticket, rules, signals, severity, why it opened.\n"
    "allocation — assign or dispatch a technician, who can go on site, send someone."
)


class ChatState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    ticket_id: str
    route: Route | None
    pending_action: dict | None


def last_human_text(messages: list[AnyMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content if isinstance(msg.content, str) else ""
    return ""


def parse_route(reply: str) -> Route:
    if "allocation" in reply.lower():
        return "allocation"
    return "qa"


def compile_ticket_chat(db: Session, ticket_id: str):
    settings = get_settings()
    router_model = init_chat_model(settings.chat_model, temperature=0)
    qa_app = compile_qa_agent(db, ticket_id)
    allocation_app = compile_allocation_agent(db, ticket_id)

    def orchestrator_node(state: ChatState) -> dict:
        text = last_human_text(state["messages"])
        if not text.strip():
            return {"route": "qa"}
        reply = router_model.invoke(
            [
                SystemMessage(content=ROUTER_SYSTEM_PROMPT),
                HumanMessage(content=text),
            ]
        )
        content = reply.content if isinstance(reply.content, str) else str(reply.content)
        return {"route": parse_route(content)}

    def qa_agent_node(state: ChatState) -> dict:
        n = len(state["messages"])
        out = qa_app.invoke(
            {"ticket_id": state["ticket_id"], "messages": state["messages"]}
        )
        return {"messages": out["messages"][n:], "pending_action": None}

    def allocation_agent_node(state: ChatState) -> dict:
        n = len(state["messages"])
        out = allocation_app(
            {"ticket_id": state["ticket_id"], "messages": state["messages"]}
        )
        new_messages = out["messages"][n:]
        pending = find_pending_action(out["messages"])
        return {"messages": new_messages, "pending_action": pending}

    def route_after_orchestrator(state: ChatState) -> Route:
        if state.get("route") == "allocation":
            return "allocation"
        return "qa"

    g = StateGraph(ChatState)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("qa_agent", qa_agent_node)
    g.add_node("allocation_agent", allocation_agent_node)
    g.add_edge(START, "orchestrator")
    g.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {"qa": "qa_agent", "allocation": "allocation_agent"},
    )
    g.add_edge("qa_agent", END)
    g.add_edge("allocation_agent", END)
    return g.compile()
