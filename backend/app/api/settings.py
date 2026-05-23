from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.config import settings
from app.db.models import User

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsOut(BaseModel):
    vllm_endpoint: str
    vllm_model: str
    # Note: not exposing JWT_SECRET, DATABASE_URL, or QM_MASTER_KEY.


@router.get("", response_model=SettingsOut)
async def get_settings(_user: User = Depends(get_current_user)) -> SettingsOut:
    return SettingsOut(
        vllm_endpoint=settings.VLLM_ENDPOINT,
        vllm_model=settings.VLLM_MODEL,
    )
