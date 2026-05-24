from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

Dialect = Literal["postgres", "sqlite", "clickhouse"]

# Which query language family an engine speaks. The agent (planner/validator/
# executor) routes on this so non-SQL backends (es_dsl, mongo_agg) can plug in
# later without changing the SQL ones. SQL covers postgres/sqlite/clickhouse.
QueryKind = Literal["sql", "es_dsl", "mongo_agg"]


class ColumnMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    data_type: str
    nullable: bool
    is_pk: bool = False
    is_unique: bool = False
    is_id: bool = False
    fk_to: str | None = None


class ColumnSample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distinct_values: list[Any] | None = None
    distinct_truncated: bool = False
    numeric_stats: dict[str, float] | None = None
    sample_rows: list[Any] | None = None
    non_null_count: int | None = None


class ForeignKeyMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_columns: list[str]
    to_table: str
    to_columns: list[str]


class TableMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: str
    name: str
    columns: list[ColumnMeta]
    foreign_keys: list[ForeignKeyMeta] = Field(default_factory=list)
    row_count_estimate: int | None = None


class SchemaBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dialect: Dialect
    tables: list[TableMeta]
    samples: dict[str, dict[str, ColumnSample]] = Field(default_factory=dict)


class ResultSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: list[str]
    dtypes: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool = False
    took_ms: int


class ValidationFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    node_kind: str | None = None


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    rewritten_sql: str | None = None
    findings: list[ValidationFinding] = Field(default_factory=list)


@runtime_checkable
class QueryEngine(Protocol):
    dialect: Dialect
    query_kind: QueryKind  # "sql" for the SQL family

    async def introspect_schema(self) -> SchemaBundle: ...

    async def sample_column(self, table: TableMeta, col: ColumnMeta) -> ColumnSample: ...

    def validate_readonly(self, sql: str) -> ValidationResult: ...

    async def execute(
        self, sql: str, *, row_cap: int = 1000, timeout_s: int = 10
    ) -> ResultSet: ...

    async def probe_write_access(self) -> bool:
        """Return True if the connection's credentials CAN write.

        This is the read-only defense Layer 1 boundary check (PLAN.md):
        attempt a harmless write (e.g. CREATE TEMP TABLE) and report
        whether it succeeded. A True result means the user supplied
        over-privileged credentials and should be warned.
        """
        ...

    async def aclose(self) -> None: ...
