from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import SchemaBundle as SchemaBundleRow, User, Workspace
from app.db.session import get_db

router = APIRouter(prefix="/workspaces", tags=["schema"])


@router.get("/{workspace_id}/schema")
async def get_workspace_schema(
    workspace_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    ws = await session.get(Workspace, workspace_id)
    if ws is None or ws.owner_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")

    row = await session.execute(
        select(SchemaBundleRow).where(SchemaBundleRow.workspace_id == workspace_id)
    )
    bundle_row = row.scalar_one_or_none()
    if bundle_row is None:
        return {
            "workspace_id": str(workspace_id),
            "status": ws.status,
            "bundle": None,
            "message": "Schema not profiled yet. Wait for the profile job to finish.",
        }

    return {
        "workspace_id": str(workspace_id),
        "status": bundle_row.status,
        "refreshed_at": bundle_row.refreshed_at.isoformat(),
        "schema_hash": bundle_row.schema_hash,
        "bundle": bundle_row.bundle,
    }
