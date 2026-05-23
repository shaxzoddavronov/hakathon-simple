from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable
from uuid import UUID


@dataclass(frozen=True)
class Resolved:
    workspace_id: UUID


@dataclass(frozen=True)
class Ambiguous:
    candidate_ids: list[UUID]


@dataclass(frozen=True)
class Conflict:
    dropdown_id: UUID
    mention_id: UUID


@dataclass(frozen=True)
class Missing:
    pass


Resolution = Resolved | Ambiguous | Conflict | Missing


_EXPLICIT_PATTERN = re.compile(r"(?:@|\[)([A-Za-z0-9_\- ]+?)\]?(?=\s|$|[,.;])")


def resolve(
    message: str,
    dropdown_id: UUID | None,
    user_workspaces: Iterable[object],
) -> Resolution:
    """Pick the workspace this message refers to.

    Signal precedence:
      1. Explicit @-mention or [bracketed] name (most authoritative).
      2. Bare-word match of any workspace name in the message text.
      3. The dropdown selection.
      4. Nothing -> Missing.

    Any branch can return Ambiguous (multiple distinct mentions) or
    Conflict (bare match disagrees with the dropdown).
    """
    by_name: dict[str, UUID] = {
        getattr(w, "name").lower(): getattr(w, "id") for w in user_workspaces
    }

    # 1. Explicit @mention or [bracket]
    explicit_names = _EXPLICIT_PATTERN.findall(message)
    explicit_ids = [
        by_name[n.strip().lower()]
        for n in explicit_names
        if n.strip().lower() in by_name
    ]
    if explicit_ids:
        unique = list(dict.fromkeys(explicit_ids))
        if len(unique) == 1:
            return Resolved(unique[0])
        return Ambiguous(unique)

    # 2. Bare-word match
    bare_ids: list[UUID] = []
    for name, wid in by_name.items():
        if re.search(rf"\b{re.escape(name)}\b", message, re.IGNORECASE):
            bare_ids.append(wid)
    unique_bare = list(dict.fromkeys(bare_ids))
    if len(unique_bare) == 1:
        match = unique_bare[0]
        if dropdown_id is not None and match != dropdown_id:
            return Conflict(dropdown_id=dropdown_id, mention_id=match)
        return Resolved(match)
    if len(unique_bare) > 1:
        return Ambiguous(unique_bare)

    # 3. Fall back to dropdown
    if dropdown_id is not None:
        return Resolved(dropdown_id)

    return Missing()


__all__ = ["resolve", "Resolved", "Ambiguous", "Conflict", "Missing", "Resolution"]
