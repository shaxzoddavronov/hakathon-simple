from __future__ import annotations

import json
import logging

from app.agents.state import GraphState
from app.services.engine_loader import build_engine_for_workspace

log = logging.getLogger(__name__)


async def run(state: GraphState) -> GraphState:
    attempts = int(state.get("executor_attempts", 0)) + 1
    plan = state.get("plan")
    validation = state.get("validation")
    workspace_id = state.get("resolved_workspace_id")

    if plan is None or validation is None or not validation.ok or workspace_id is None:
        return {"last_executor_error": "executor invoked without a valid plan"}

    try:
        engine = await build_engine_for_workspace(workspace_id)
    except Exception as exc:
        log.exception("engine load failed")
        return {"executor_attempts": attempts, "last_executor_error": str(exc)}

    try:
        if state.get("query_kind") == "mongo_agg":
            pipeline = json.loads(plan.pipeline_json)
            rs = await engine.run_pipeline(plan.collection, pipeline)
            executed = f"db.{plan.collection}.aggregate({plan.pipeline_json})"
        else:
            executed = validation.rewritten_sql or plan.sql
            rs = await engine.execute(executed)
    except Exception as exc:
        log.exception("execute failed")
        return {"executor_attempts": attempts, "last_executor_error": str(exc)}
    finally:
        await engine.aclose()

    return {
        "result": rs,
        "sql_executed": executed,
        "executor_attempts": attempts,
        "last_executor_error": None,
    }
