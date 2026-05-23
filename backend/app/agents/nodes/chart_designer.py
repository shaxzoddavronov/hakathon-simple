from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agents.llm import get_llm
from app.agents.state import GraphState
from app.engines.base import ResultSet
from app.schemas.ui_spec import (
    BarSpec,
    ColumnDef,
    KPI,
    LineSpec,
    PieSpec,
    TableSpec,
    TextOnly,
    UISpec,
)

# Cap chart series length so a 1000-row result doesn't produce a giant spec.
_MAX_CHART_ROWS = 100


class ChartChoice(BaseModel):
    """The LLM picks the *shape*; we fill the data from the real ResultSet.

    This keeps the model from inventing numbers — it only sees the column
    names + 5 sample rows and decides how to visualize them.
    """

    model_config = ConfigDict(extra="forbid")

    chart_type: Literal["kpi", "bar", "line", "pie", "table", "text_only"]
    title: str
    x_column: str | None = Field(
        default=None, description="Category or time column for bar/line."
    )
    y_columns: list[str] = Field(
        default_factory=list, description="Measure columns for bar/line."
    )
    label_column: str | None = Field(default=None, description="Slice label for pie.")
    value_column: str | None = Field(
        default=None, description="Measure for pie / single value for kpi."
    )


_SYSTEM = (
    "You choose how to visualize the result of a SQL query. You are given "
    "the column names and 5 sample rows — never the full data. Pick the best "
    "chart_type:\n"
    "- kpi: a single scalar (one row, one measure)\n"
    "- bar: a category column (x_column) vs one or more measures (y_columns)\n"
    "- line: an ordered time/date x_column vs measures\n"
    "- pie: a label_column + a single value_column, few slices\n"
    "- table: many columns or no obvious chart\n"
    "- text_only: nothing to chart\n"
    "Only name columns that appear in the column list."
)


def _shape(rs: ResultSet) -> str:
    return (
        f"columns: {rs.columns}\n"
        f"row_count: {rs.row_count}\n"
        f"sample_rows (first 5): {rs.rows[:5]}\n"
    )


def _jsonable(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (_dt.date, _dt.datetime)):
        return v.isoformat()
    return v


def _rows_as_dicts(rs: ResultSet, limit: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rs.rows[:limit]:
        out.append({col: _jsonable(val) for col, val in zip(rs.columns, row)})
    return out


def _build_spec(choice: ChartChoice, rs: ResultSet) -> UISpec:
    """Construct a concrete UISpec from the LLM's choice + the real rows.

    Falls back to a table whenever the chosen columns don't line up with
    the actual result — better an honest table than a broken chart.
    """
    cols = set(rs.columns)
    ct = choice.chart_type

    if ct == "text_only":
        return TextOnly(type="text_only", body_md=choice.title or "No chart.")

    if ct == "kpi":
        val_col = choice.value_column if choice.value_column in cols else (rs.columns[0] if rs.columns else None)
        if val_col and rs.rows:
            raw = rs.rows[0][rs.columns.index(val_col)]
            value = _jsonable(raw)
            return KPI(type="kpi", label=choice.title or val_col, value=value)
        return _fallback_table(rs, choice.title)

    if ct == "bar":
        y = [c for c in choice.y_columns if c in cols]
        if choice.x_column in cols and y:
            return BarSpec(
                type="bar",
                title=choice.title,
                x=choice.x_column,
                y=y,
                data=_rows_as_dicts(rs, _MAX_CHART_ROWS),
            )
        return _fallback_table(rs, choice.title)

    if ct == "line":
        y = [c for c in choice.y_columns if c in cols]
        if choice.x_column in cols and y:
            return LineSpec(
                type="line",
                title=choice.title,
                x=choice.x_column,
                y=y,
                data=_rows_as_dicts(rs, _MAX_CHART_ROWS),
            )
        return _fallback_table(rs, choice.title)

    if ct == "pie":
        if choice.label_column in cols and choice.value_column in cols:
            return PieSpec(
                type="pie",
                title=choice.title,
                label=choice.label_column,
                value=choice.value_column,
                data=_rows_as_dicts(rs, _MAX_CHART_ROWS),
            )
        return _fallback_table(rs, choice.title)

    return _fallback_table(rs, choice.title)


def _fallback_table(rs: ResultSet, title: str | None) -> TableSpec:
    columns = [ColumnDef(key=c, label=c) for c in rs.columns]
    rows = [[_jsonable(v) for v in row] for row in rs.rows[:_MAX_CHART_ROWS]]
    return TableSpec(type="table", columns=columns, rows=rows)


async def run(state: GraphState) -> GraphState:
    rs = state.get("result")
    if rs is None:
        return {"chart": None}
    if rs.row_count == 0:
        return {"chart": TextOnly(type="text_only", body_md="No rows returned.")}

    llm = get_llm()
    try:
        choice = await llm.structured(
            [
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": f"Question: {state.get('user_message','')}\n\n"
                    f"Result shape:\n{_shape(rs)}\nReturn a ChartChoice.",
                },
            ],
            ChartChoice,
        )
    except Exception:
        # If the model misbehaves, an honest table still answers the question.
        return {"chart": _fallback_table(rs, None)}

    return {"chart": _build_spec(choice, rs)}
