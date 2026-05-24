from __future__ import annotations

import time
from typing import Any

import clickhouse_connect

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


@register("clickhouse")
class ClickHouseEngine:
    """ClickHouse adapter (SQL family).

    Read-only is defense-in-depth, same as Postgres:
      - Boundary: connect with a read-only ClickHouse user.
      - Parse: validate_readonly(sql, dialect="clickhouse") via sqlglot.
      - Runtime: every query runs with the `readonly=2` setting (no
        INSERT/ALTER/CREATE) plus max_execution_time / max_result_rows.
    """

    dialect: Dialect = "clickhouse"
    query_kind: QueryKind = "sql"

    def __init__(self, workspace) -> None:
        meta = dict(workspace.connection_meta or {})
        creds = getattr(workspace, "_credentials", None) or {}
        meta.update(creds)
        # db_name keeps parity with the Postgres connection_meta shape.
        self._database = meta.get("db_name") or meta.get("database") or "default"
        required = {"host"}
        missing = required - meta.keys()
        if missing:
            raise ValueError(
                f"ClickHouse workspace missing connection keys: {sorted(missing)}"
            )
        self._kwargs = {
            "host": meta["host"],
            "port": int(meta.get("port", 8123)),
            "username": meta.get("user", "default"),
            "password": meta.get("password", ""),
            "database": self._database,
            "secure": bool(meta.get("ssl", False)),
        }

    async def _client(self):
        return await clickhouse_connect.get_async_client(**self._kwargs)

    async def introspect_schema(self) -> SchemaBundle:
        client = await self._client()
        try:
            db = self._database
            trows = (
                await client.query(
                    "SELECT name, total_rows FROM system.tables "
                    "WHERE database = {db:String} AND engine NOT LIKE '%View' "
                    "ORDER BY name",
                    parameters={"db": db},
                )
            ).result_rows
            crows = (
                await client.query(
                    "SELECT table, name, type, is_in_primary_key "
                    "FROM system.columns WHERE database = {db:String} "
                    "ORDER BY table, position",
                    parameters={"db": db},
                )
            ).result_rows

            cols_by_table: dict[str, list[ColumnMeta]] = {}
            for table, name, ctype, in_pk in crows:
                cols_by_table.setdefault(table, []).append(
                    ColumnMeta(
                        name=name,
                        data_type=str(ctype),
                        nullable=str(ctype).startswith("Nullable"),
                        is_pk=bool(in_pk),
                    )
                )

            tables = [
                TableMeta(
                    schema=db,
                    name=name,
                    columns=cols_by_table.get(name, []),
                    foreign_keys=[],  # ClickHouse has no foreign keys
                    row_count_estimate=int(total) if total is not None else None,
                )
                for name, total in trows
            ]
            return SchemaBundle(dialect=self.dialect, tables=tables)
        finally:
            await client.close()

    async def sample_column(self, table: TableMeta, col: ColumnMeta) -> ColumnSample:
        if col.is_id:
            return ColumnSample()
        client = await self._client()
        try:
            qt = f"`{table.name}`"
            qc = f"`{col.name}`"
            settings = {"readonly": 2, "max_execution_time": 8}
            row = (
                await client.query(
                    f"SELECT count() AS rc, uniqExact({qc}) AS dc FROM {qt}",
                    settings=settings,
                )
            ).result_rows
            rc, dc = (int(row[0][0]), int(row[0][1])) if row else (0, 0)

            dt = col.data_type.lower()
            is_numeric = any(k in dt for k in ("int", "float", "decimal", "double"))
            is_text = any(k in dt for k in ("string", "fixedstring"))
            categorical = is_text or (rc > 0 and dc <= 50 and dc / max(rc, 1) < 0.05)

            if categorical:
                vals = (
                    await client.query(
                        f"SELECT {qc} AS v FROM {qt} WHERE {qc} IS NOT NULL "
                        f"GROUP BY {qc} LIMIT 51",
                        settings=settings,
                    )
                ).result_rows
                flat = [r[0] for r in vals]
                return ColumnSample(
                    distinct_values=flat[:50], distinct_truncated=len(flat) > 50
                )
            if is_numeric:
                s = (
                    await client.query(
                        f"SELECT min({qc}), max({qc}), avg({qc}) FROM {qt}",
                        settings=settings,
                    )
                ).result_rows
                stats: dict[str, float] = {}
                if s:
                    for k, v in zip(("min", "max", "avg"), s[0]):
                        if v is not None:
                            stats[k] = float(v)
                return ColumnSample(numeric_stats=stats)
            sample = (
                await client.query(
                    f"SELECT {qc} FROM {qt} WHERE {qc} IS NOT NULL LIMIT 5",
                    settings=settings,
                )
            ).result_rows
            return ColumnSample(sample_rows=[r[0] for r in sample], non_null_count=rc)
        finally:
            await client.close()

    def validate_readonly(self, sql: str) -> ValidationResult:
        return validate_readonly(sql, dialect="clickhouse")

    async def probe_write_access(self) -> bool:
        client = await self._client()
        try:
            try:
                await client.command(
                    "CREATE TEMPORARY TABLE _qm_probe (x Int8) ENGINE = Memory"
                )
                return True
            except Exception:
                return False
        finally:
            await client.close()

    async def execute(
        self, sql: str, *, row_cap: int = 1000, timeout_s: int = 10
    ) -> ResultSet:
        client = await self._client()
        try:
            started = time.perf_counter()
            result = await client.query(
                sql,
                settings={
                    "readonly": 2,  # no writes; data read only
                    "max_execution_time": timeout_s,
                    "max_result_rows": row_cap + 1,
                    "result_overflow_mode": "break",
                },
            )
            took_ms = int((time.perf_counter() - started) * 1000)
            columns = list(result.column_names)
            raw_rows: list[Any] = list(result.result_rows)
            truncated = len(raw_rows) > row_cap
            rows = [list(r) for r in raw_rows[:row_cap]]
            return ResultSet(
                columns=columns,
                dtypes=[""] * len(columns),
                rows=rows,
                row_count=len(rows),
                truncated=truncated,
                took_ms=took_ms,
            )
        finally:
            await client.close()

    async def aclose(self) -> None:
        return None
