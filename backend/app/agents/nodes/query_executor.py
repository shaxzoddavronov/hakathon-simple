from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agents.state import GraphState
from app.config import settings
from app.db.models import Workspace, WorkspaceCredentials
from app.engines import register_all as register_engines
from app.engines.registry import get_engine
from app.services import crypto

log = logging.getLogger(__name__)


async def run(state: GraphState) -> GraphState:
    attempts = int(state.get("executor_attempts", 0)) + 1
    plan = state.get("plan")
    validation = state.get("validation")
    workspace_id = state.get("resolved_workspace_id")

    if plan is None or validation is None or not validation.ok or workspace_id is None:
        return {"last_executor_error": "executor invoked without a valid plan"}

    register_engines()
    sql_to_run = validation.rewritten_sql or plan.sql

    sa_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    Session = async_sessionmaker(sa_engine, expire_on_commit=False)
    try:
        async with Session() as session:
            ws = await session.get(Workspace, workspace_id)
            creds_row = (
                await session.execute(
                    select(WorkspaceCredentials).where(
                        WorkspaceCredentials.workspace_id == workspace_id
                    )
                )
            ).scalar_one_or_none()

            if ws is None:
                return {
                    "executor_attempts": attempts,
                    "last_executor_error": f"workspace {workspace_id} not found",
                }

            creds: dict[str, str] = {}
            if creds_row is not None:
                raw = crypto.decrypt(
                    creds_row.ciphertext, creds_row.nonce, key_version=creds_row.key_version
                )
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                    if isinstance(parsed, dict):
                        creds = {str(k): str(v) for k, v in parsed.items()}
                except Exception:
                    creds = {"password": raw.decode("utf-8", errors="replace")}

            ws._credentials = creds  # type: ignore[attr-defined]
            engine = get_engine(ws)
    finally:
        await sa_engine.dispose()

    try:
        rs = await engine.execute(sql_to_run)
    except Exception as exc:
        log.exception("execute failed")
        return {
            "executor_attempts": attempts,
            "last_executor_error": str(exc),
        }
    finally:
        await engine.aclose()

    return {
        "result": rs,
        "sql_executed": sql_to_run,
        "executor_attempts": attempts,
        "last_executor_error": None,
    }
