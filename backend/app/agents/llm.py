from __future__ import annotations

import time
from typing import Any, TypeVar

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Thin wrapper around the OpenAI-compatible vLLM endpoint.

    Every structured call passes a Pydantic-derived JSON Schema as
    ``response_format`` so vLLM's ``xgrammar`` backend constrains
    decoding. We never parse free-text JSON from the model.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        model: str | None = None,
        api_key: str = "not-needed",
    ) -> None:
        self._endpoint = endpoint or settings.VLLM_ENDPOINT
        self._model = model or settings.VLLM_MODEL
        self._client = AsyncOpenAI(base_url=self._endpoint, api_key=api_key)
        self._ready_cache: tuple[float, bool] | None = None  # (checked_at, ok)

    @property
    def model(self) -> str:
        return self._model

    async def is_ready(self, *, ttl_s: float = 5.0) -> bool:
        """Cheap reachability probe against vLLM's /models, cached for ttl_s.

        Used by the chat endpoint to fail fast with 503 rather than start a
        stream that will die mid-flight when the model server is down.
        """
        now = time.monotonic()
        if self._ready_cache is not None:
            checked_at, ok = self._ready_cache
            if now - checked_at < ttl_s:
                return ok
        url = f"{self._endpoint.rstrip('/')}/models"
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                resp = await client.get(url)
                ok = resp.status_code < 500
        except Exception:
            ok = False
        self._ready_cache = (now, ok)
        return ok

    async def structured(
        self,
        messages: list[dict[str, Any]],
        response_model: type[T],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> T:
        """Call the model and parse the response into ``response_model``."""
        schema = response_model.model_json_schema()
        completion = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": schema,
                    "strict": True,
                },
            },
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = completion.choices[0].message.content or ""
        return response_model.model_validate_json(text)


_default_client: LLMClient | None = None


def get_llm() -> LLMClient:
    """Return a process-wide LLMClient — created lazily."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


def set_llm_for_testing(client: LLMClient | None) -> None:
    """Hook so tests can swap the client with a stub."""
    global _default_client
    _default_client = client


__all__ = ["LLMClient", "get_llm", "set_llm_for_testing"]
