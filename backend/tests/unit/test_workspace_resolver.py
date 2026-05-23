from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.workspace_resolver import (
    Ambiguous,
    Conflict,
    Missing,
    Resolved,
    resolve,
)


def _ws(name: str):
    return SimpleNamespace(id=uuid4(), name=name)


def test_dropdown_only() -> None:
    ws = _ws("Core_Analytics")
    out = resolve("show me total revenue", ws.id, [ws])
    assert isinstance(out, Resolved)
    assert out.workspace_id == ws.id


def test_at_mention_overrides_dropdown() -> None:
    a, b = _ws("Core_Analytics"), _ws("Sales_DW")
    out = resolve("@Sales_DW give me last week's orders", a.id, [a, b])
    assert isinstance(out, Resolved)
    assert out.workspace_id == b.id


def test_bracket_mention() -> None:
    a, b = _ws("Core_Analytics"), _ws("Sales_DW")
    out = resolve("[Core_Analytics] show me totals", None, [a, b])
    assert isinstance(out, Resolved)
    assert out.workspace_id == a.id


def test_ambiguous_mentions() -> None:
    a, b = _ws("alpha"), _ws("beta")
    out = resolve("@alpha then @beta", None, [a, b])
    assert isinstance(out, Ambiguous)
    assert set(out.candidate_ids) == {a.id, b.id}


def test_bare_word_match() -> None:
    ws = _ws("sales")
    out = resolve("what are total sales by region", None, [ws])
    assert isinstance(out, Resolved)
    assert out.workspace_id == ws.id


def test_bare_word_conflict_with_dropdown() -> None:
    a, b = _ws("sales"), _ws("hr")
    out = resolve("show me sales totals", b.id, [a, b])
    assert isinstance(out, Conflict)
    assert out.dropdown_id == b.id
    assert out.mention_id == a.id


def test_missing_when_no_signals() -> None:
    a = _ws("sales")
    out = resolve("hi", None, [a])
    assert isinstance(out, Missing)


def test_explicit_takes_priority_over_bare() -> None:
    a, b = _ws("sales"), _ws("hr")
    # 'sales' is a bare match but @hr is explicit and wins.
    out = resolve("@hr give me sales numbers", None, [a, b])
    assert isinstance(out, Resolved)
    assert out.workspace_id == b.id
