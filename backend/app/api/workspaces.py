from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.models import ProfileJob, User, Workspace, WorkspaceCredentials
from app.db.session import get_db
from app.engines import register_all as register_engines
from app.engines.registry import get_engine
from app.services import crypto

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    dialect: Literal["postgres", "sqlite"]
    connection_meta: dict[str, Any] = Field(default_factory=dict)
    auth_kind: Literal["password", "dsn", "iam", "none"] = "password"
    credentials: dict[str, str] = Field(default_factory=dict)


class WorkspaceOut(BaseModel):
    id: str
    name: str
    dialect: str
    status: str
    profile_job_id: str | None = None
    table_count: int | None = None
    last_synced_at: str | None = None


class ProbeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dialect: Literal["postgres", "sqlite"]
    connection_meta: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, str] = Field(default_factory=dict)


class ProbeResult(BaseModel):
    reachable: bool
    can_write: bool
    message: str


@router.post("/probe", response_model=ProbeResult)
async def probe_connection(
    payload: ProbeRequest,
    _user: User = Depends(get_current_user),
) -> ProbeResult:
    """Read-only defense Layer 1: test the connection and warn if the
    supplied credentials have write access. Persists nothing."""
    register_engines()
    ws_like = SimpleNamespace(
        dialect=payload.dialect,
        connection_meta=payload.connection_meta,
        _credentials=payload.credentials,
    )
    try:
        engine = get_engine(ws_like)
    except Exception as exc:
        return ProbeResult(reachable=False, can_write=False, message=f"Bad config: {exc}")

    try:
        can_write = await engine.probe_write_access()
    except Exception as exc:
        return ProbeResult(
            reachable=False,
            can_write=False,
            message=f"Could not connect: {exc}",
        )
    finally:
        await engine.aclose()

    if can_write:
        return ProbeResult(
            reachable=True,
            can_write=True,
            message=(
                "Connected, but these credentials can WRITE to the database. "
                "We strongly recommend a read-only role."
            ),
        )
    return ProbeResult(
        reachable=True,
        can_write=False,
        message="Connected. Credentials are read-only. ✓",
    )


@router.post(
    "",
    response_model=WorkspaceOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    payload: CreateWorkspaceRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceOut:
    ws = Workspace(
        owner_id=current_user.id,
        name=payload.name,
        dialect=payload.dialect,
        connection_meta=payload.connection_meta,
        status="pending",
    )
    session.add(ws)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A workspace with that name already exists",
        ) from exc

    if payload.credentials and payload.auth_kind != "none":
        blob = json.dumps(payload.credentials, sort_keys=True).encode("utf-8")
        ciphertext, nonce, key_version = crypto.encrypt(blob, aad=str(ws.id).encode())
        creds_row = WorkspaceCredentials(
            workspace_id=ws.id,
            auth_kind=payload.auth_kind,
            ciphertext=ciphertext,
            nonce=nonce,
            key_version=key_version,
        )
        session.add(creds_row)

    job = ProfileJob(workspace_id=ws.id, state="queued")
    session.add(job)
    await session.commit()
    await session.refresh(ws)
    await session.refresh(job)

    _enqueue_profile_job(str(ws.id), str(job.id))

    return WorkspaceOut(
        id=str(ws.id),
        name=ws.name,
        dialect=ws.dialect,
        status=ws.status,
        profile_job_id=str(job.id),
    )


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkspaceOut]:
    rows = await session.execute(
        select(Workspace)
        .where(Workspace.owner_id == current_user.id)
        .options(selectinload(Workspace.schema_bundle))
        .order_by(Workspace.created_at.desc())
    )
    out: list[WorkspaceOut] = []
    for w in rows.scalars().all():
        bundle = w.schema_bundle
        tables = (bundle.bundle or {}).get("tables") if bundle else None
        out.append(
            WorkspaceOut(
                id=str(w.id),
                name=w.name,
                dialect=w.dialect,
                status=w.status,
                table_count=len(tables) if isinstance(tables, list) else None,
                last_synced_at=(
                    bundle.refreshed_at.isoformat()
                    if bundle and bundle.refreshed_at
                    else None
                ),
            )
        )
    return out


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    workspace_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceOut:
    ws = await session.get(Workspace, workspace_id)
    if ws is None or ws.owner_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    return WorkspaceOut(id=str(ws.id), name=ws.name, dialect=ws.dialect, status=ws.status)


@router.post("/{workspace_id}/refresh", response_model=WorkspaceOut)
async def refresh_workspace(
    workspace_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceOut:
    """Re-profile a workspace: enqueue a fresh ProfileJob and flip the
    workspace back to 'profiling'."""
    ws = await session.get(Workspace, workspace_id)
    if ws is None or ws.owner_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")

    ws.status = "profiling"
    job = ProfileJob(workspace_id=ws.id, state="queued")
    session.add(job)
    await session.commit()
    await session.refresh(job)

    _enqueue_profile_job(str(ws.id), str(job.id))

    return WorkspaceOut(
        id=str(ws.id),
        name=ws.name,
        dialect=ws.dialect,
        status=ws.status,
        profile_job_id=str(job.id),
    )


def _enqueue_profile_job(workspace_id: str, profile_job_id: str) -> None:
    """Enqueue the Celery profile task. Isolated so tests can monkeypatch."""
    from app.workers.profile_task import run_profile_job

    run_profile_job.delay(workspace_id, profile_job_id)
