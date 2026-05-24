from __future__ import annotations

import time
from typing import Any

import httpx

from app.engines.base import (
    ColumnMeta,
    ColumnSample,
    Dialect,
    QueryKind,
    ResultSet,
    SchemaBundle,
    TableMeta,
    ValidationResult,
)
from app.engines.registry import register
from app.services.readonly_validator import validate_readonly


@register("elasticsearch")
class ElasticsearchEngine:
    """Elasticsearch adapter via the read-only `_sql` API.

    ES SQL is SELECT-only by design (it rejects writes), and returns
    {columns, rows} that map straight onto ResultSet. Read-only defense:
      - Boundary: connect with a read-privileged ES user.
      - Parse: validate_readonly(sql, dialect="elasticsearch") via sqlglot.
      - Runtime: the _sql endpoint cannot mutate data.
    Indices are "tables"; mapping fields are "columns".
    """

    dialect: Dialect = "elasticsearch"
    query_kind: QueryKind = "sql"

    def __init__(self, workspace) -> None:
        meta = dict(workspace.connection_meta or {})
        creds = getattr(workspace, "_credentials", None) or {}
        meta.update(creds)
        required = {"host"}
        missing = required - meta.keys()
        if missing:
            raise ValueError(
                f"Elasticsearch workspace missing connection keys: {sorted(missing)}"
            )
        scheme = "https" if meta.get("ssl") else "http"
        self._base = f"{scheme}://{meta['host']}:{int(meta.get('port', 9200))}"
        user = meta.get("user")
        self._auth = (user, meta.get("password", "")) if user else None

    def _client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base, auth=self._auth, timeout=timeout)

    async def _sql(self, client: httpx.AsyncClient, query: str, fetch_size: int) -> dict:
        r = await client.post(
            "/_sql", params={"format": "json"}, json={"query": query, "fetch_size": fetch_size}
        )
        if r.status_code >= 400:
            # Surface the ES reason (e.g. "Arrays returned by [tags] are not
            # supported") so the planner↔executor retry loop can re-plan with
            # explicit scalar columns instead of SELECT *.
            try:
                reason = r.json().get("error", {}).get("reason", r.text)
            except Exception:
                reason = r.text
            raise RuntimeError(f"Elasticsearch SQL error: {reason}")
        return r.json()

    async def introspect_schema(self) -> SchemaBundle:
        async with self._client(20.0) as client:
            tbls = await self._sql(client, "SHOW TABLES", 1000)
            # SHOW TABLES columns: catalog, name, type, kind
            name_idx = next(
                (i for i, c in enumerate(tbls["columns"]) if c["name"] == "name"), 1
            )
            type_idx = next(
                (i for i, c in enumerate(tbls["columns"]) if c["name"] == "type"), 2
            )
            indices = [
                row[name_idx]
                for row in tbls.get("rows", [])
                if str(row[type_idx]).upper() == "TABLE"
            ][:50]

            tables: list[TableMeta] = []
            for index in indices:
                try:
                    desc = await self._sql(client, f'DESCRIBE "{index}"', 1000)
                except Exception:
                    continue
                # DESCRIBE columns: column, type, mapping
                cols: list[ColumnMeta] = []
                for row in desc.get("rows", []):
                    col_name = str(row[0])
                    es_type = str(row[1]) if len(row) > 1 else "unknown"
                    if "." in col_name or es_type.lower() in ("unsupported", "object", "nested"):
                        continue  # skip sub-fields / non-queryable
                    cols.append(
                        ColumnMeta(name=col_name, data_type=es_type, nullable=True)
                    )
                tables.append(
                    TableMeta(schema="", name=index, columns=cols, foreign_keys=[])
                )
            return SchemaBundle(dialect=self.dialect, tables=tables)

    async def sample_column(self, table: TableMeta, col: ColumnMeta) -> ColumnSample:
        # Best-effort: ES SQL aggregations require aggregatable (keyword/numeric)
        # fields; failures must not break profiling.
        dt = col.data_type.lower()
        try:
            async with self._client(8.0) as client:
                if dt in ("keyword", "boolean"):
                    res = await self._sql(
                        client,
                        f'SELECT "{col.name}" FROM "{table.name}" '
                        f'GROUP BY "{col.name}" LIMIT 51',
                        51,
                    )
                    vals = [r[0] for r in res.get("rows", [])]
                    return ColumnSample(
                        distinct_values=vals[:50], distinct_truncated=len(vals) > 50
                    )
                if any(k in dt for k in ("long", "integer", "double", "float", "short", "byte")):
                    res = await self._sql(
                        client,
                        f'SELECT MIN("{col.name}"), MAX("{col.name}"), AVG("{col.name}") '
                        f'FROM "{table.name}"',
                        1,
                    )
                    rows = res.get("rows", [])
                    stats: dict[str, float] = {}
                    if rows:
                        for k, v in zip(("min", "max", "avg"), rows[0]):
                            if v is not None:
                                stats[k] = float(v)
                    return ColumnSample(numeric_stats=stats)
        except Exception:
            pass
        return ColumnSample()

    def validate_readonly(self, sql: str) -> ValidationResult:
        return validate_readonly(sql, dialect="elasticsearch")

    async def probe_write_access(self) -> bool:
        try:
            async with self._client(6.0) as client:
                r = await client.post(
                    "/_security/user/_has_privileges",
                    json={
                        "index": [
                            {"names": ["*"], "privileges": ["write", "create_index"]}
                        ]
                    },
                )
                if r.status_code == 200:
                    return bool(r.json().get("has_all_requested"))
        except Exception:
            pass
        return False

    async def execute(
        self, sql: str, *, row_cap: int = 1000, timeout_s: int = 10
    ) -> ResultSet:
        async with self._client(float(timeout_s + 2)) as client:
            started = time.perf_counter()
            res = await self._sql(client, sql, row_cap)
            took_ms = int((time.perf_counter() - started) * 1000)
            columns = [c["name"] for c in res.get("columns", [])]
            raw_rows: list[Any] = res.get("rows", [])
            truncated = bool(res.get("cursor")) or len(raw_rows) > row_cap
            rows = [list(r) for r in raw_rows[:row_cap]]
            return ResultSet(
                columns=columns,
                dtypes=[""] * len(columns),
                rows=rows,
                row_count=len(rows),
                truncated=truncated,
                took_ms=took_ms,
            )

    async def aclose(self) -> None:
        return None
