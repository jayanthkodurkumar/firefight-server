from typing import Annotated

from langchain.chat_models import init_chat_model
from langchain.messages import AnyMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from sqlalchemy.orm import Session
from typing_extensions import TypedDict

from app.core.config.settings import get_settings
from app.features.chat.tools import build_qa_tools

QA_SYSTEM_PROMPT = (
    "You help field engineers understand one BMS ticket. "
    "Use tools for facts; do not guess numbers or rule thresholds. "
    "Ticket: {ticket_id}"
)


class QaAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    ticket_id: str


def compile_qa_agent(db: Session, ticket_id: str):
    settings = get_settings()
    tools = build_qa_tools(db, ticket_id)
    tools_by_name = {}
    for t in tools:
        tools_by_name[t.name] = t
    model = init_chat_model(settings.chat_model, temperature=0).bind_tools(tools)

    def llm_call(state: QaAgentState):
        system = SystemMessage(
            content=QA_SYSTEM_PROMPT.format(ticket_id=state["ticket_id"])
        )
        reply = model.invoke([system] + state["messages"])
        return {"messages": [reply]}

    def tool_node(state: QaAgentState):
        out = []
        for tc in state["messages"][-1].tool_calls:
            out.append(
                ToolMessage(
                    content=tools_by_name[tc["name"]].invoke(tc["args"]),
                    tool_call_id=tc["id"],
                )
            )
        return {"messages": out}

    def should_continue(state: QaAgentState):
        if state["messages"][-1].tool_calls:
            return "tool_node"
        return END

    g = StateGraph(QaAgentState)
    g.add_node("llm_call", llm_call)
    g.add_node("tool_node", tool_node)
    g.add_edge(START, "llm_call")
    g.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
    g.add_edge("tool_node", "llm_call")
    return g.compile()
