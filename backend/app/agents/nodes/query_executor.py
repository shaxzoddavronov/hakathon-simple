from __future__ import annotations

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

    sql_to_run = validation.rewritten_sql or plan.sql

    try:
        engine = await build_engine_for_workspace(workspace_id)
    except Exception as exc:
        log.exception("engine load failed")
        return {"executor_attempts": attempts, "last_executor_error": str(exc)}

    try:
        rs = await engine.execute(sql_to_run)
    except Exception as exc:
        log.exception("execute failed")
        return {"executor_attempts": attempts, "last_executor_error": str(exc)}
    finally:
        await engine.aclose()

    return {
        "result": rs,
        "sql_executed": sql_to_run,
        "executor_attempts": attempts,
        "last_executor_error": None,
    }
