"""Per-user LLM settings: DB override merged over env defaults.

Stored in the `settings` table under key "llm" as a JSON blob
{endpoint, api_key, model_chat, model_profile}. Any missing field falls
back to the env default in app.config. This is what makes the model /
endpoint / token user-editable instead of hardcoded.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Settings as SettingsRow

_KEY = "llm"


async def get_llm_settings(session: AsyncSession, user_id: UUID) -> dict[str, str]:
    """Effective LLM settings for a user — DB override → env default."""
    row = await session.get(SettingsRow, (user_id, _KEY))
    val = row.value if row and isinstance(row.value, dict) else {}
    return {
        "endpoint": val.get("endpoint") or settings.VLLM_ENDPOINT,
        "api_key": val.get("api_key") or settings.VLLM_API_KEY,
        "model_chat": val.get("model_chat") or settings.VLLM_MODEL,
        "model_profile": val.get("model_profile") or settings.VLLM_MODEL_PROFILE,
    }


async def save_llm_settings(
    session: AsyncSession,
    user_id: UUID,
    *,
    endpoint: str | None = None,
    api_key: str | None = None,
    model_chat: str | None = None,
    model_profile: str | None = None,
) -> dict[str, str]:
    """Upsert the user's LLM settings. Only non-None fields are written;
    an empty api_key string is ignored so the token isn't wiped by a blank
    form field (send a real value to change it)."""
    row = await session.get(SettingsRow, (user_id, _KEY))
    val = dict(row.value) if row and isinstance(row.value, dict) else {}
    if endpoint is not None:
        val["endpoint"] = endpoint
    if api_key:
        val["api_key"] = api_key
    if model_chat is not None:
        val["model_chat"] = model_chat
    if model_profile is not None:
        val["model_profile"] = model_profile
    if row is None:
        session.add(SettingsRow(user_id=user_id, key=_KEY, value=val))
    else:
        row.value = val  # reassign so SQLAlchemy flags the JSON change
    await session.commit()
    return val
