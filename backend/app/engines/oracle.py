from __future__ import annotations

import time
from typing import Any

import oracledb

from app.engines.base import (
    ColumnMeta,
    ColumnSample,
    Dialect,
    ForeignKeyMeta,
    QueryKind,
    ResultSet,
    SchemaBundle,
    TableMeta,
    ValidationResult,
)
from app.engines.registry import register
from app.services.readonly_validator import validate_readonly


@register("oracle")
class OracleEngine:
    """Oracle adapter (SQL family), python-oracledb thin mode (no client lib).

    Read-only defense-in-depth:
      - Boundary: connect with a user that only has SELECT grants.
      - Parse: validate_readonly(sql, dialect="oracle") via sqlglot.
      - Runtime: SET TRANSACTION READ ONLY (DML errors) + call_timeout.
    Introspection uses USER_* views (the connected schema's own objects).
    """

    dialect: Dialect = "oracle"
    query_kind: QueryKind = "sql"

    def __init__(self, workspace) -> None:
        meta = dict(workspace.connection_meta or {})
        creds = getattr(workspace, "_credentials", None) or {}
        meta.update(creds)
        required = {"host", "user", "password"}
        missing = required - meta.keys()
        if missing:
            raise ValueError(
                f"Oracle workspace missing connection keys: {sorted(missing)}"
            )
        host = meta["host"]
        port = int(meta.get("port", 1521))
        # db_name doubles as the Oracle service name (Easy Connect).
        service = meta.get("db_name") or meta.get("service_name") or "FREEPDB1"
        self._dsn = f"{host}:{port}/{service}"
        self._user = meta["user"]
        self._password = meta["password"]

    async def _connect(self):
        return await oracledb.connect_async(
            user=self._user, password=self._password, dsn=self._dsn
        )

    async def introspect_schema(self) -> SchemaBundle:
        conn = await self._connect()
        try:
            cur = conn.cursor()
            await cur.execute("SELECT table_name FROM user_tables ORDER BY table_name")
            table_names = [r[0] for r in await cur.fetchall()]

            await cur.execute(
                "SELECT table_name, column_name, data_type, nullable "
                "FROM user_tab_columns ORDER BY table_name, column_id"
            )
            cols_by_table: dict[str, list[ColumnMeta]] = {}
            for tname, cname, dtype, nullable in await cur.fetchall():
                cols_by_table.setdefault(tname, []).append(
                    ColumnMeta(
                        name=cname,
                        data_type=str(dtype),
                        nullable=(nullable == "Y"),
                    )
                )

            # Primary keys
            await cur.execute(
                "SELECT cc.table_name, cc.column_name "
                "FROM user_constraints c "
                "JOIN user_cons_columns cc ON c.constraint_name = cc.constraint_name "
                "WHERE c.constraint_type = 'P'"
            )
            pk: set[tuple[str, str]] = {(r[0], r[1]) for r in await cur.fetchall()}

            # Foreign keys
            fks_by_table: dict[str, list[ForeignKeyMeta]] = {}
            try:
                await cur.execute(
                    "SELECT a.table_name, a.column_name, pk.table_name, b.column_name "
                    "FROM user_cons_columns a "
                    "JOIN user_constraints c ON a.constraint_name = c.constraint_name "
                    "  AND c.constraint_type = 'R' "
                    "JOIN user_constraints pk ON c.r_constraint_name = pk.constraint_name "
                    "JOIN user_cons_columns b ON pk.constraint_name = b.constraint_name "
                    "  AND b.position = a.position"
                )
                for tname, fcol, rtable, rcol in await cur.fetchall():
                    fks_by_table.setdefault(tname, []).append(
                        ForeignKeyMeta(
                            from_columns=[fcol], to_table=rtable, to_columns=[rcol]
                        )
                    )
            except Exception:
                pass

            tables: list[TableMeta] = []
            for tname in table_names:
                cols = cols_by_table.get(tname, [])
                for col in cols:
                    if (tname, col.name) in pk:
                        col.is_pk = True
                for fk in fks_by_table.get(tname, []):
                    for col in cols:
                        if col.name in fk.from_columns:
                            col.fk_to = f"{fk.to_table}.{fk.to_columns[0]}"
                tables.append(
                    TableMeta(
                        schema=self._user.upper(),
                        name=tname,
                        columns=cols,
                        foreign_keys=fks_by_table.get(tname, []),
                    )
                )
            return SchemaBundle(dialect=self.dialect, tables=tables)
        finally:
            await conn.close()

    async def sample_column(self, table: TableMeta, col: ColumnMeta) -> ColumnSample:
        if col.is_id:
            return ColumnSample()
        conn = await self._connect()
        try:
            conn.call_timeout = 8000
            cur = conn.cursor()
            qt = f'"{table.name}"'
            qc = f'"{col.name}"'
            await cur.execute(f"SELECT COUNT(*), COUNT(DISTINCT {qc}) FROM {qt}")
            row = await cur.fetchone()
            rc, dc = (int(row[0]), int(row[1])) if row else (0, 0)

            dt = col.data_type.lower()
            is_numeric = any(k in dt for k in ("number", "float", "integer", "decimal"))
            is_text = any(k in dt for k in ("char", "clob"))
            categorical = is_text or (rc > 0 and dc <= 50 and dc / max(rc, 1) < 0.05)

            if categorical:
                await cur.execute(
                    f"SELECT {qc} FROM {qt} WHERE {qc} IS NOT NULL "
                    f"GROUP BY {qc} FETCH FIRST 51 ROWS ONLY"
                )
                vals = [r[0] for r in await cur.fetchall()]
                return ColumnSample(
                    distinct_values=vals[:50], distinct_truncated=len(vals) > 50
                )
            if is_numeric:
                await cur.execute(
                    f"SELECT MIN({qc}), MAX({qc}), AVG({qc}) FROM {qt}"
                )
                s = await cur.fetchone()
                stats: dict[str, float] = {}
                if s:
                    for k, v in zip(("min", "max", "avg"), s):
                        if v is not None:
                            stats[k] = float(v)
                return ColumnSample(numeric_stats=stats)
            await cur.execute(
                f"SELECT {qc} FROM {qt} WHERE {qc} IS NOT NULL FETCH FIRST 5 ROWS ONLY"
            )
            return ColumnSample(
                sample_rows=[r[0] for r in await cur.fetchall()], non_null_count=rc
            )
        finally:
            await conn.close()

    def validate_readonly(self, sql: str) -> ValidationResult:
        return validate_readonly(sql, dialect="oracle")

    async def probe_write_access(self) -> bool:
        """Report whether the credentials hold any write privilege (read-only
        check against SESSION_PRIVS — no side effects, since Oracle DDL can't
        be rolled back)."""
        conn = await self._connect()
        try:
            cur = conn.cursor()
            await cur.execute(
                "SELECT COUNT(*) FROM session_privs WHERE privilege IN "
                "('CREATE TABLE','CREATE ANY TABLE','INSERT ANY TABLE',"
                "'UPDATE ANY TABLE','DELETE ANY TABLE','DROP ANY TABLE')"
            )
            row = await cur.fetchone()
            return bool(row and int(row[0]) > 0)
        finally:
            await conn.close()

    async def execute(
        self, sql: str, *, row_cap: int = 1000, timeout_s: int = 10
    ) -> ResultSet:
        conn = await self._connect()
        try:
            conn.call_timeout = timeout_s * 1000  # statement timeout (ms)
            cur = conn.cursor()
            started = time.perf_counter()
            await cur.execute("SET TRANSACTION READ ONLY")  # runtime read-only
            await cur.execute(sql)
            columns = [d[0] for d in (cur.description or [])]
            fetched: list[Any] = await cur.fetchmany(row_cap + 1)
            took_ms = int((time.perf_counter() - started) * 1000)
            truncated = len(fetched) > row_cap
            rows = [list(r) for r in fetched[:row_cap]]
            return ResultSet(
                columns=columns,
                dtypes=[""] * len(columns),
                rows=rows,
                row_count=len(rows),
                truncated=truncated,
                took_ms=took_ms,
            )
        finally:
            await conn.close()

    async def aclose(self) -> None:
        return None
