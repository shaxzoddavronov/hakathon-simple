from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.services.user_settings import get_llm_settings, save_llm_settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsOut(BaseModel):
    vllm_endpoint: str
    vllm_model_chat: str
    vllm_model_profile: str
    has_token: bool  # never echo the token itself
    available_models: list[str]


class SettingsUpdate(BaseModel):
    # All optional — only provided fields are changed. An empty/omitted token
    # leaves the existing one untouched.
    vllm_endpoint: str | None = None
    vllm_token: str | None = None
    vllm_model_chat: str | None = None
    vllm_model_profile: str | None = None


async def _list_models(endpoint: str, api_key: str) -> list[str]:
    """Best-effort list of model ids the endpoint serves (for the dropdowns)."""
    url = endpoint.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=4.0) as c:
            r = await c.get(url, headers=headers)
            data = r.json().get("data", [])
            ids = [m["id"] for m in data if isinstance(m, dict) and m.get("id")]
            # Only Qwen models are supported — hide everything else (e.g. gemma).
            return [m for m in ids if "qwen" in m.lower()]
    except Exception:
        return []


async def _out(cfg: dict[str, str]) -> SettingsOut:
    return SettingsOut(
        vllm_endpoint=cfg["endpoint"],
        vllm_model_chat=cfg["model_chat"],
        vllm_model_profile=cfg["model_profile"],
        has_token=bool(cfg["api_key"]),
        available_models=await _list_models(cfg["endpoint"], cfg["api_key"]),
    )


@router.get("", response_model=SettingsOut)
async def get_settings(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SettingsOut:
    return await _out(await get_llm_settings(session, user.id))


@router.put("", response_model=SettingsOut)
async def update_settings(
    payload: SettingsUpdate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SettingsOut:
    await save_llm_settings(
        session,
        user.id,
        endpoint=payload.vllm_endpoint,
        api_key=payload.vllm_token,
        model_chat=payload.vllm_model_chat,
        model_profile=payload.vllm_model_profile,
    )
    return await _out(await get_llm_settings(session, user.id))
