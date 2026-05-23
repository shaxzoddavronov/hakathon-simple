from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Dialect = Literal["postgres", "sqlite"]


class ColumnSample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distinct_values: list[Any] | None = None
    distinct_truncated: bool = False
    numeric_stats: dict[str, float] | None = None
    sample_rows: list[Any] | None = None
    non_null_count: int | None = None


class ColumnMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    data_type: str
    nullable: bool
    is_pk: bool = False
    is_unique: bool = False
    is_id: bool = False
    fk_to: str | None = None


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
