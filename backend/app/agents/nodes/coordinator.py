from __future__ import annotations

from app.agents.llm import get_llm
from app.agents.state import GraphState
from app.schemas.llm_io import IntentDecision

_SYSTEM = (
    "You are the routing brain of QueryMind, an NL-to-SQL assistant. "
    "Classify each user message into ONE intent:\n"
    "- chitchat: greetings / capability questions / off-topic\n"
    "- metadata: asks about the database SHAPE (what tables, what columns)\n"
    "- data_query: asks for actual rows / aggregates / a single chart\n"
    "- dashboard: asks for a multi-panel overview / KPIs side by side\n"
    "- clarify: ambiguous about which workspace OR what the user wants\n"
    "Also extract `workspace_hint` if the message names a specific connected DB."
)


async def run(state: GraphState) -> GraphState:
    msg = state.get("user_message", "")
    if not msg:
        return {"intent": "clarify", "error_message": "empty user message"}

    if state.get("force_dashboard"):
        # Dashboard-Diagram mode: the user explicitly asked for a dashboard,
        # so skip LLM classification and route straight to the dashboard path.
        out: GraphState = {"intent": "dashboard", "workspace_hint": None}
    else:
        llm = get_llm()
        decision = await llm.structured(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": msg},
            ],
            IntentDecision,
        )
        out = {
            "intent": decision.intent,
            "workspace_hint": decision.workspace_hint,
        }
    # Default resolved_workspace_id to whatever the dropdown picked. The
    # workspace_resolver is wired in by the API layer before invoking the
    # graph; here we just carry whatever's already in state.
    if "resolved_workspace_id" not in state:
        out["resolved_workspace_id"] = state.get("active_workspace_id")
    return out
