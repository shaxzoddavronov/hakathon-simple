from __future__ import annotations

import datetime as _dt
import json
import time
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from app.engines.base import (
    ColumnMeta,
    ColumnSample,
    Dialect,
    QueryKind,
    ResultSet,
    SchemaBundle,
    TableMeta,
    ValidationResult,
    ValidationFinding,
)
from app.engines.registry import register

_SAMPLE = 100  # docs sampled per collection for schema inference


def _infer_type(v: Any) -> str:
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "double"
    if isinstance(v, str):
        return "string"
    if isinstance(v, _dt.datetime):
        return "datetime"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__  # e.g. ObjectId


def _jsonable(v: Any) -> Any:
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, _dt.datetime):
        return v.isoformat()
    if isinstance(v, (dict, list)):
        return json.dumps(v, default=str)
    return str(v)  # ObjectId, Decimal128, etc.


@register("mongodb")
class MongoEngine:
    """MongoDB adapter (non-SQL: aggregation pipelines).

    Read-only defense-in-depth:
      - Boundary: connect with a read-only Mongo role.
      - Parse: validate_mongo_pipeline() rejects $out/$merge/$function/$where.
      - Runtime: only aggregate() is ever called — never a write method.
    Schema is inferred by sampling docs (Mongo is schemaless); collections
    are "tables" and inferred fields are "columns".
    """

    dialect: Dialect = "mongodb"
    query_kind: QueryKind = "mongo_agg"

    def __init__(self, workspace) -> None:
        meta = dict(workspace.connection_meta or {})
        creds = getattr(workspace, "_credentials", None) or {}
        meta.update(creds)
        required = {"host", "db_name"}
        missing = required - meta.keys()
        if missing:
            raise ValueError(
                f"MongoDB workspace missing connection keys: {sorted(missing)}"
            )
        self._db_name = meta["db_name"]
        host = meta["host"]
        port = int(meta.get("port", 27017))
        user = meta.get("user")
        if user:
            auth_source = meta.get("auth_source", "admin")
            pw = meta.get("password", "")
            self._uri = (
                f"mongodb://{user}:{pw}@{host}:{port}/"
                f"?authSource={auth_source}"
            )
        else:
            self._uri = f"mongodb://{host}:{port}/"
        self._tls = bool(meta.get("ssl", False))

    def _client(self) -> AsyncIOMotorClient:
        return AsyncIOMotorClient(
            self._uri, tls=self._tls, serverSelectionTimeoutMS=5000
        )

    async def introspect_schema(self) -> SchemaBundle:
        client = self._client()
        try:
            db = client[self._db_name]
            names = await db.list_collection_names()
            tables: list[TableMeta] = []
            for coll in sorted(names):
                if coll.startswith("system."):
                    continue
                docs = await db[coll].find({}).limit(_SAMPLE).to_list(_SAMPLE)
                field_type: dict[str, str] = {}
                for d in docs:
                    for k, v in d.items():
                        if k not in field_type and v is not None:
                            field_type[k] = _infer_type(v)
                cols = [
                    ColumnMeta(name=k, data_type=t, nullable=True, is_id=(k == "_id"))
                    for k, t in field_type.items()
                ]
                try:
                    rc = await db[coll].estimated_document_count()
                except Exception:
                    rc = None
                tables.append(
                    TableMeta(
                        schema=self._db_name,
                        name=coll,
                        columns=cols,
                        foreign_keys=[],
                        row_count_estimate=rc,
                    )
                )
            return SchemaBundle(dialect=self.dialect, tables=tables)
        finally:
            client.close()

    async def sample_column(self, table: TableMeta, col: ColumnMeta) -> ColumnSample:
        if col.is_id:
            return ColumnSample()
        client = self._client()
        try:
            db = client[self._db_name]
            # Best-effort distinct values (cap 50).
            try:
                vals = await db[table.name].distinct(col.name)
                vals = [_jsonable(v) for v in vals[:51]]
                if vals:
                    return ColumnSample(
                        distinct_values=vals[:50], distinct_truncated=len(vals) > 50
                    )
            except Exception:
                pass
            return ColumnSample()
        finally:
            client.close()

    def validate_readonly(self, sql: str) -> ValidationResult:
        # Mongo doesn't use SQL; the agent validates the pipeline via
        # services.mongo_validator. This stub exists only for the Protocol.
        return ValidationResult(
            ok=False,
            findings=[
                ValidationFinding(
                    code="NOT_SQL", message="MongoDB uses aggregation pipelines, not SQL."
                )
            ],
        )

    async def probe_write_access(self) -> bool:
        client = self._client()
        try:
            status = await client[self._db_name].command({"connectionStatus": 1})
            roles = status.get("authInfo", {}).get("authenticatedUserRoles", [])
            if not roles:
                # No auth / unknown — assume writable (advisory only).
                return True
            writable = {"readWrite", "dbOwner", "dbAdmin", "root", "__system", "readWriteAnyDatabase"}
            return any(r.get("role") in writable for r in roles)
        except Exception:
            return False
        finally:
            client.close()

    async def run_pipeline(
        self,
        collection: str,
        pipeline: list[dict],
        *,
        row_cap: int = 1000,
        timeout_s: int = 10,
    ) -> ResultSet:
        client = self._client()
        try:
            db = client[self._db_name]
            started = time.perf_counter()
            cursor = db[collection].aggregate(pipeline, maxTimeMS=timeout_s * 1000)
            docs = await cursor.to_list(row_cap + 1)
            took_ms = int((time.perf_counter() - started) * 1000)

            # Flatten docs → columns (ordered union of keys) + rows.
            columns: list[str] = []
            seen: set[str] = set()
            for d in docs[:row_cap]:
                for k in d.keys():
                    if k not in seen:
                        seen.add(k)
                        columns.append(k)
            rows = [[_jsonable(d.get(k)) for k in columns] for d in docs[:row_cap]]
            return ResultSet(
                columns=columns,
                dtypes=[""] * len(columns),
                rows=rows,
                row_count=len(rows),
                truncated=len(docs) > row_cap,
                took_ms=took_ms,
            )
        finally:
            client.close()

    async def execute(
        self, sql: str, *, row_cap: int = 1000, timeout_s: int = 10
    ) -> ResultSet:
        raise RuntimeError("MongoDB uses run_pipeline(), not SQL execute().")

    async def aclose(self) -> None:
        return None
