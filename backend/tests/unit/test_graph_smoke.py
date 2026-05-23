from __future__ import annotations

import pytest

from app.agents import llm as llm_module
from app.agents.graph import build_graph
from app.schemas.llm_io import AnswerDraft, IntentDecision, SqlPlan


class StubLLM:
    """A canned responder keyed by response model type.

    Returns whichever model instance was registered for the requested
    ``response_model``. Raises if a type was not registered — fail loud.
    """

    def __init__(self) -> None:
        self._by_type: dict[type, object] = {}
        self.calls: list[type] = []

    def register(self, model_cls, instance) -> None:
        self._by_type[model_cls] = instance

    async def structured(self, messages, response_model, **_kw):
        self.calls.append(response_model)
        if response_model not in self._by_type:
            raise AssertionError(f"StubLLM has no canned response for {response_model.__name__}")
        return self._by_type[response_model]


@pytest.fixture()
def stub_llm(monkeypatch):
    stub = StubLLM()
    monkeypatch.setattr(llm_module, "_default_client", stub)
    yield stub
    monkeypatch.setattr(llm_module, "_default_client", None)


@pytest.mark.asyncio
async def test_chitchat_path_runs_to_completion(stub_llm: StubLLM) -> None:
    stub_llm.register(
        IntentDecision,
        IntentDecision(intent="chitchat", workspace_hint=None),
    )
    stub_llm.register(
        AnswerDraft,
        AnswerDraft(
            headline="Hi!",
            body_md="QueryMind lets you ask questions about your databases.",
        ),
    )

    graph = build_graph()
    final = await graph.ainvoke({"user_message": "hi"})

    assert final.get("intent") == "chitchat"
    ui = final.get("ui_spec")
    assert ui is not None
    assert ui.type == "text_only"
    assert "QueryMind" in ui.body_md


@pytest.mark.asyncio
async def test_clarify_emits_text_only(stub_llm: StubLLM) -> None:
    stub_llm.register(
        IntentDecision,
        IntentDecision(intent="clarify", workspace_hint=None),
    )

    graph = build_graph()
    final = await graph.ainvoke({"user_message": "??"})
    assert final.get("intent") == "clarify"
    # finalizer with no chart/answer/error -> fallback text_only
    ui = final.get("ui_spec")
    assert ui is not None
    assert ui.type == "text_only"
