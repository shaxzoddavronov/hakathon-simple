"""Typed application settings, loaded from environment / .env file.

All runtime configuration enters the app through this module — never read
`os.environ` directly elsewhere. Fields mirror ``backend/.env.example``.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Values come from (in order of precedence): process environment, then
    the ``.env`` file at the backend root. Unknown keys are ignored so a
    shared ``.env`` can hold both backend- and infra-level variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application metadata DB -------------------------------------------------
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./querymind.db",
        description="Async SQLAlchemy URL for the QueryMind metadata DB.",
    )

    # --- Broker / cache ----------------------------------------------------------
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # --- Auth --------------------------------------------------------------------
    JWT_SECRET: str = Field(default="dev-insecure-change-me")
    JWT_ALG: str = Field(default="HS256")
    JWT_EXPIRES_MIN: int = Field(default=60, ge=1)

    # --- Credential-at-rest encryption ------------------------------------------
    # Url-safe base64-encoded 32-byte key. See `.env.example` for a generator.
    QM_MASTER_KEY: str = Field(default="REPLACE_WITH_BASE64_32_BYTE_KEY")

    # --- Local LLM (vLLM, OpenAI-compatible) ------------------------------------
    VLLM_ENDPOINT: str = Field(default="http://localhost:8000/v1")
    VLLM_MODEL: str = Field(default="Qwen/Qwen2.5-0.5B-Instruct")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide singleton ``Settings`` instance."""
    return Settings()


# Convenience alias so callers can do ``from app.config import settings``.
settings = get_settings()
