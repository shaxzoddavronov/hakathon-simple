from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class ColumnDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    dtype: Literal["int", "float", "string", "bool", "datetime", "date"] = "string"
    align: Literal["left", "right", "center"] = "left"


class TextOnly(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["text_only"]
    body_md: str


class KPI(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["kpi"]
    label: str
    value: float | str
    unit: str | None = None
    delta: float | None = None
    sparkline: list[float] = Field(default_factory=list)


class BarSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["bar"]
    title: str
    x: str
    y: list[str]
    data: list[dict[str, Any]]
    stacked: bool = False


class LineSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["line"]
    title: str
    x: str
    y: list[str]
    data: list[dict[str, Any]]


class PieSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["pie"]
    title: str
    label: str
    value: str
    data: list[dict[str, Any]]


class TableSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["table"]
    columns: list[ColumnDef]
    rows: list[list[Any]]


class GridChild(BaseModel):
    model_config = ConfigDict(extra="forbid")

    span: int = Field(ge=1, le=12)
    spec: "UISpec"


class Dashboard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["dashboard"]
    title: str
    children: list[GridChild]


UISpec = Annotated[
    Union[TextOnly, KPI, BarSpec, LineSpec, PieSpec, TableSpec, Dashboard],
    Field(discriminator="type"),
]


GridChild.model_rebuild()
