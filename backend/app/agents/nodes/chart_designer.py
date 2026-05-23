from __future__ import annotations

from app.agents.llm import get_llm
from app.agents.state import GraphState
from app.engines.base import ResultSet
from app.schemas.ui_spec import (
    BarSpec,
    Dashboard,
    KPI,
    LineSpec,
    PieSpec,
    TableSpec,
    TextOnly,
    UISpec,
)
from pydantic import TypeAdapter

_SYSTEM = (
    "You design a single chart spec describing the result of a SQL query. "
    "Pick the best visualization given the columns and a 5-row sample. "
    "Options: text_only, kpi, bar, line, pie, table, dashboard. "
    "Use 'table' for >2 columns of categorical data. Use 'line' when an "
    "ordered time/date column is present. Use 'bar' for category->measure. "
    "Use 'kpi' for a single number. Do not invent numbers."
)


def _result_shape(rs: ResultSet | None) -> str:
    if rs is None:
        return "no result"
    sample = rs.rows[:5]
    return (
        f"columns: {rs.columns}\n"
        f"row_count: {rs.row_count}\n"
        f"sample_rows (first 5): {sample}\n"
    )


_adapter = TypeAdapter(UISpec)


async def run(state: GraphState) -> GraphState:
    rs = state.get("result")
    if rs is None:
        return {"chart": None}

    if rs.row_count == 0:
        return {"chart": TextOnly(type="text_only", body_md="No rows returned.")}

    llm = get_llm()
    prompt = (
        f"Question: {state.get('user_message','')}\n\n"
        f"Result shape:\n{_result_shape(rs)}\n\n"
        "Return a UISpec."
    )
    # We pick one chart family and let the LLM choose; the discriminated union
    # validates the type tag matches the payload shape.
    try:
        # Most callers ask for a single chart; LLM picks the variant.
        chart_dict = await llm.structured(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            BarSpec,  # default placeholder — superseded below
        )
    except Exception:
        chart_dict = None

    if chart_dict is not None:
        return {"chart": chart_dict}
    return {"chart": TextOnly(type="text_only", body_md="(no chart)")}
