from langchain.chat_models import init_chat_model
from langchain.messages import AnyMessage, SystemMessage, ToolMessage
from sqlalchemy.orm import Session
from typing_extensions import TypedDict

from app.core.config.settings import get_settings
from app.features.chat.tools.allocation_tools import build_allocation_tools

ALLOCATION_SYSTEM_PROMPT = (
    "You help assign field technicians to a BMS ticket. "
    "Always call list_eligible_technicians first to get real technician ids. "
    "If the user asks who to send, who to dispatch, who should go, or similar, "
    "pick the best match (skill, region, on_call when urgent) and call propose_assignment "
    "in the same turn—do not ask the user to paste a technician id. "
    "Briefly explain your pick in the final message; the UI will show an approve button from propose_assignment. "
    "Only skip propose_assignment if the user clearly wants a list only (e.g. 'list options', 'don't assign yet'). "
    "Do not invent technician ids. Ticket: {ticket_id}"
)

MAX_TOOL_ROUNDS = 10


class AllocationAgentState(TypedDict):
    messages: list[AnyMessage]
    ticket_id: str


def compile_allocation_agent(db: Session, ticket_id: str):
    settings = get_settings()
    tools_by_name = {}
    for tool in build_allocation_tools(db, ticket_id):
        tools_by_name[tool.name] = tool
    model = init_chat_model(settings.chat_model, temperature=0).bind_tools(
        list(tools_by_name.values())
    )

    def invoke(state: AllocationAgentState) -> AllocationAgentState:
        messages = list(state["messages"])
        tid = state["ticket_id"]
        system = SystemMessage(content=ALLOCATION_SYSTEM_PROMPT.format(ticket_id=tid))

        for _ in range(MAX_TOOL_ROUNDS):
            reply = model.invoke([system] + messages)
            messages.append(reply)
            if not reply.tool_calls:
                break
            for tc in reply.tool_calls:
                result = tools_by_name[tc["name"]].invoke(tc["args"])
                messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))
        else:
            raise RuntimeError("allocation agent exceeded max tool rounds")

        return {"ticket_id": tid, "messages": messages}

    return invoke
