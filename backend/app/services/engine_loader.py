from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models import Workspace, WorkspaceCredentials
from app.engines import register_all as register_engines
from app.engines.base import QueryEngine
from app.engines.registry import get_engine
from app.services import crypto


async def build_engine_for_workspace(workspace_id: UUID) -> QueryEngine:
    """Load a workspace + its (AES-GCM, AAD=workspace.id) credentials from the
    metadata DB and return a ready-to-use QueryEngine for the user's data DB.

    The concrete engine copies connection params into itself at __init__, so
    the returned engine remains valid after the metadata session/engine close.
    Caller owns closing the returned engine via ``await engine.aclose()``.
    """
    register_engines()
    sa_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    Session = async_sessionmaker(sa_engine, expire_on_commit=False)
    try:
        async with Session() as session:
            ws = await session.get(Workspace, workspace_id)
            if ws is None:
                raise ValueError(f"workspace {workspace_id} not found")
            creds_row = (
                await session.execute(
                    select(WorkspaceCredentials).where(
                        WorkspaceCredentials.workspace_id == workspace_id
                    )
                )
            ).scalar_one_or_none()

            creds: dict[str, str] = {}
            if creds_row is not None:
                raw = crypto.decrypt(
                    creds_row.ciphertext,
                    creds_row.nonce,
                    key_version=creds_row.key_version,
                    aad=str(workspace_id).encode(),
                )
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                    if isinstance(parsed, dict):
                        creds = {str(k): str(v) for k, v in parsed.items()}
                    else:
                        creds = {"password": raw.decode("utf-8", errors="replace")}
                except Exception:
                    creds = {"password": raw.decode("utf-8", errors="replace")}

            ws._credentials = creds  # type: ignore[attr-defined]
            return get_engine(ws)
    finally:
        await sa_engine.dispose()


__all__ = ["build_engine_for_workspace"]
