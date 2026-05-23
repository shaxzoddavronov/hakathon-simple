from __future__ import annotations

from decimal import Decimal

import pytest

from app.agents import llm as llm_module
from app.agents.nodes.chart_designer import ChartChoice, run
from app.engines.base import ResultSet


def _rs(columns, rows, **kw) -> ResultSet:
    return ResultSet(
        columns=columns,
        dtypes=[""] * len(columns),
        rows=rows,
        row_count=len(rows),
        took_ms=1,
        **kw,
    )


class OneShotLLM:
    """Returns a fixed ChartChoice for the next structured() call."""

    def __init__(self, choice: ChartChoice | None) -> None:
        self._choice = choice

    async def structured(self, _messages, response_model, **_kw):
        if self._choice is None:
            raise RuntimeError("model unavailable")
        return self._choice


@pytest.fixture(autouse=True)
def _reset_llm():
    yield
    llm_module.set_llm_for_testing(None)


async def _run_with(choice, rs):
    llm_module.set_llm_for_testing(OneShotLLM(choice))
    return await run({"user_message": "q", "result": rs})


@pytest.mark.asyncio
async def test_bar_built_from_real_rows() -> None:
    rs = _rs(["region", "total"], [["EU", 225.0], ["NA", 150.0], ["APAC", 75.0]])
    choice = ChartChoice(chart_type="bar", title="Revenue by region", x_column="region", y_columns=["total"])
    out = await _run_with(choice, rs)
    chart = out["chart"]
    assert chart.type == "bar"
    assert chart.x == "region"
    assert chart.y == ["total"]
    # data comes from the ResultSet, not the LLM
    assert {d["region"] for d in chart.data} == {"EU", "NA", "APAC"}
    assert any(d["total"] == 225.0 for d in chart.data)


@pytest.mark.asyncio
async def test_kpi_single_value() -> None:
    rs = _rs(["total"], [[Decimal("450.00")]])
    choice = ChartChoice(chart_type="kpi", title="Total revenue", value_column="total")
    out = await _run_with(choice, rs)
    chart = out["chart"]
    assert chart.type == "kpi"
    assert chart.value == 450.0  # Decimal coerced to float


@pytest.mark.asyncio
async def test_pie_built() -> None:
    rs = _rs(["region", "total"], [["EU", 225.0], ["NA", 150.0]])
    choice = ChartChoice(chart_type="pie", title="Share", label_column="region", value_column="total")
    out = await _run_with(choice, rs)
    assert out["chart"].type == "pie"
    assert out["chart"].label == "region"


@pytest.mark.asyncio
async def test_bad_columns_fall_back_to_table() -> None:
    rs = _rs(["region", "total"], [["EU", 225.0]])
    # x_column doesn't exist → must not produce a broken bar
    choice = ChartChoice(chart_type="bar", title="x", x_column="nonexistent", y_columns=["total"])
    out = await _run_with(choice, rs)
    assert out["chart"].type == "table"


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_table() -> None:
    rs = _rs(["a", "b"], [[1, 2]])
    out = await _run_with(None, rs)  # OneShotLLM raises
    assert out["chart"].type == "table"


@pytest.mark.asyncio
async def test_empty_result_text_only() -> None:
    rs = _rs(["a"], [])
    out = await _run_with(ChartChoice(chart_type="bar", title="x"), rs)
    assert out["chart"].type == "text_only"
