from __future__ import annotations

from app.agents.state import GraphState
from app.services.mongo_validator import validate_mongo_pipeline
from app.services.readonly_validator import validate_readonly


async def run(state: GraphState) -> GraphState:
    plan = state.get("plan")
    if plan is None:
        return {"last_validation_error": "no plan to validate"}

    if state.get("query_kind") == "mongo_agg":
        result = validate_mongo_pipeline(plan.pipeline_json)
    else:
        result = validate_readonly(plan.sql, dialect=plan.dialect)
    out: GraphState = {"validation": result}
    if not result.ok:
        codes = ", ".join(f.code for f in result.findings) or "unknown"
        out["last_validation_error"] = f"{codes}: " + "; ".join(f.message for f in result.findings[:3])
    return out
