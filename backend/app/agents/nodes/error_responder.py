from __future__ import annotations

from app.agents.state import GraphState
from app.schemas.ui_spec import TextOnly


async def run(state: GraphState) -> GraphState:
    parts: list[str] = []
    if state.get("last_validation_error"):
        parts.append(f"The query I drafted failed validation: {state['last_validation_error']}.")
    if state.get("last_executor_error"):
        parts.append(f"Execution failed: {state['last_executor_error']}.")
    if state.get("error_message"):
        parts.append(state["error_message"])
    if not parts:
        parts.append("I could not satisfy this request.")

    msg = " ".join(parts) + " Try rephrasing or narrowing the question."
    return {"ui_spec": TextOnly(type="text_only", body_md=msg)}
