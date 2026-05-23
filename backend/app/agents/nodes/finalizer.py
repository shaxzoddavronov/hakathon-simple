from __future__ import annotations

from app.agents.state import GraphState
from app.schemas.ui_spec import Dashboard, GridChild, TextOnly, UISpec


async def run(state: GraphState) -> GraphState:
    chart = state.get("chart")
    answer = state.get("answer")
    error = state.get("error_message")

    if error and chart is None and answer is None:
        return {"ui_spec": TextOnly(type="text_only", body_md=f"⚠️ {error}")}

    body_md = answer.body_md if answer is not None else ""
    if chart is None and answer is not None:
        return {"ui_spec": TextOnly(type="text_only", body_md=body_md)}
    if chart is not None and answer is None:
        return {"ui_spec": chart}

    # Chart + answer: bundle as a small 2-row dashboard so the frontend
    # gets a single UISpec to render. The answer goes on top as text_only.
    if chart is not None and answer is not None:
        ui: UISpec = Dashboard(
            type="dashboard",
            title=answer.headline,
            children=[
                GridChild(span=12, spec=TextOnly(type="text_only", body_md=body_md)),
                GridChild(span=12, spec=chart),
            ],
        )
        return {"ui_spec": ui}

    return {"ui_spec": TextOnly(type="text_only", body_md="(no output)")}
