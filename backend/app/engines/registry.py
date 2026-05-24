from __future__ import annotations

from typing import Type

from app.engines.base import Dialect, QueryEngine, QueryKind

DIALECT_REGISTRY: dict[Dialect, Type[QueryEngine]] = {}

# Query-language family per dialect. The agent routes planning/validation on
# this so non-SQL backends (es_dsl, mongo_agg) plug in without touching the
# SQL ones. Keep in sync with each engine's `query_kind`.
QUERY_KIND: dict[Dialect, QueryKind] = {
    "postgres": "sql",
    "sqlite": "sql",
    "clickhouse": "sql",
    "oracle": "sql",
    # ES uses its read-only _sql API, so the agent still emits SQL.
    "elasticsearch": "sql",
}


def query_kind_for(dialect: Dialect) -> QueryKind:
    return QUERY_KIND.get(dialect, "sql")


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
