from __future__ import annotations

import re
import time
from typing import Any, TypeVar

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings

T = TypeVar("T", bound=BaseModel)


def _extract_json(text: str) -> str:
    """Best-effort: pull the JSON object/array out of a model response.

    Guided decoding usually yields clean JSON, but reasoning models may
    prepend a <think>…</think> block or prose. Strip that and slice to the
    outermost braces so model_validate_json succeeds.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    if text[:1] in "{[":
        return text
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        return text
    start = min(starts)
    end = max(text.rfind("}"), text.rfind("]"))
    return text[start : end + 1] if end > start else text


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
        api_key: str | None = None,
    ) -> None:
        self._endpoint = endpoint or settings.VLLM_ENDPOINT
        self._model = model or settings.VLLM_MODEL
        # A local vLLM ignores the key; a shared/admin endpoint authenticates
        # with it. Fall back to settings, then to a dummy for local dev.
        self._client = AsyncOpenAI(
            base_url=self._endpoint,
            api_key=api_key or settings.VLLM_API_KEY or "not-needed",
        )
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
        """Call the model and parse the response into ``response_model``.

        Reasoning models occasionally return an empty body (all reasoning, no
        JSON). We disable thinking and retry up to 3 times — nudging the
        temperature each attempt to escape a degenerate empty sample —
        before giving up.
        """
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": response_model.__name__,
                "schema": response_model.model_json_schema(),
                "strict": True,
            },
        }
        last_exc: Exception | None = None
        for attempt in range(3):
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                response_format=response_format,
                temperature=temperature + 0.15 * attempt,
                max_tokens=max_tokens,
                # We want the structured answer, not reasoning. Ignored by
                # non-thinking templates, so it's safe across models.
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            payload = _extract_json(completion.choices[0].message.content or "")
            if payload.strip():
                try:
                    return response_model.model_validate_json(payload)
                except Exception as e:  # malformed JSON — retry
                    last_exc = e
            else:
                last_exc = ValueError(
                    f"empty response for {response_model.__name__}"
                )
        raise last_exc or RuntimeError(
            f"structured() failed for {response_model.__name__}"
        )


_default_client: LLMClient | None = None


def get_llm(model: str | None = None) -> LLMClient:
    """Build a client from env config (optionally overriding the model).
    Honors a test stub when one is installed."""
    if _default_client is not None:
        return _default_client
    return LLMClient(model=model)


def agent_llm(state: dict | None = None) -> LLMClient:
    """Chat client built from the per-request LLM settings carried in graph
    state (endpoint / api_key / model), so each user's editable Settings
    take effect. Falls back to env defaults, and to the test stub in tests."""
    if _default_client is not None:
        return _default_client
    s = state or {}
    return LLMClient(
        endpoint=s.get("llm_endpoint"),
        model=s.get("llm_model"),
        api_key=s.get("llm_api_key"),
    )


def set_llm_for_testing(client: LLMClient | None) -> None:
    """Hook so tests can swap the client with a stub."""
    global _default_client
    _default_client = client


__all__ = ["LLMClient", "get_llm", "agent_llm", "set_llm_for_testing"]
