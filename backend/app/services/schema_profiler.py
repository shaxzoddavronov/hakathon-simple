from __future__ import annotations

import re

from app.engines.base import ColumnMeta, QueryEngine, SchemaBundle, TableMeta

_ID_NAME_PATTERN = re.compile(r"^(id|.*_id|uuid|guid)$", re.IGNORECASE)


def _apply_id_heuristic(col: ColumnMeta) -> None:
    if col.is_id:
        return
    if col.is_pk:
        col.is_id = True
        return
    if _ID_NAME_PATTERN.match(col.name):
        col.is_id = True
        return
    # Unique monotonic int — approximated by (is_unique AND numeric dtype).
    dt = (col.data_type or "").lower()
    if col.is_unique and any(k in dt for k in ("int", "serial", "bigint")):
        col.is_id = True


async def profile(engine: QueryEngine) -> SchemaBundle:
    """Introspect + sample every column in every table.

    Mutates the bundle's column ``is_id`` flags in-place per PLAN.md ID
    heuristic, then asks the engine for a per-column sample. Returns the
    enriched bundle with the ``samples`` map populated.
    """
    bundle = await engine.introspect_schema()
    samples: dict[str, dict[str, object]] = {}

    for table in bundle.tables:
        for col in table.columns:
            _apply_id_heuristic(col)

        table_samples: dict[str, object] = {}
        for col in table.columns:
            sample = await engine.sample_column(table, col)
            table_samples[col.name] = sample
        samples[f"{table.schema}.{table.name}"] = table_samples

    bundle.samples = samples  # type: ignore[assignment]
    return bundle


__all__ = ["profile", "_apply_id_heuristic"]
