from __future__ import annotations

from typing import Type

from app.engines.base import Dialect, QueryEngine

DIALECT_REGISTRY: dict[Dialect, Type[QueryEngine]] = {}


def register(dialect: Dialect):
    def deco(cls: Type[QueryEngine]) -> Type[QueryEngine]:
        DIALECT_REGISTRY[dialect] = cls
        return cls

    return deco


def get_engine(workspace) -> QueryEngine:
    dialect: Dialect = workspace.dialect
    if dialect not in DIALECT_REGISTRY:
        raise ValueError(
            f"No engine registered for dialect {dialect!r}. "
            f"Known: {sorted(DIALECT_REGISTRY)}"
        )
    return DIALECT_REGISTRY[dialect](workspace)
