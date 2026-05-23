from __future__ import annotations

from uuid import uuid4

import pytest

from app.agents import llm as llm_module
from app.agents.nodes import dashboard_builder
from app.engines.base import ColumnMeta, ResultSet, SchemaBundle, TableMeta
from app.schemas.llm_io import DashboardPanel, DashboardPlan


def _bundle() -> SchemaBundle:
    return SchemaBundle(
        dialect="sqlite",
        tables=[
            TableMeta(
                schema="main",
                name="sales",
                columns=[
                    ColumnMeta(name="region", data_type="text", nullable=False),
                    ColumnMeta(name="amount", data_type="real", nullable=False),
                ],
            )
        ],
    )


class StubLLM:
    def __init__(self, plan: DashboardPlan) -> None:
        self._plan = plan

    async def structured(self, _messages, response_model, **_kw):
        assert response_model is DashboardPlan
        return self._plan


class FakeEngine:
    """Returns a canned ResultSet for any SQL; records what it ran."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    async def execute(self, sql, **_kw):
        self.executed.append(sql)
        return ResultSet(
            columns=["region", "total"],
            dtypes=["", ""],
            rows=[["EU", 225.0], ["NA", 150.0]],
            row_count=2,
            took_ms=1,
        )

    async def aclose(self):
        return None


@pytest.fixture()
def _wire(monkeypatch):
    plan = DashboardPlan(
        dialect="sqlite",
        title="Sales overview",
        panels=[
            DashboardPanel(
                title="Revenue by region",
                sql="SELECT region, SUM(amount) AS total FROM sales GROUP BY region",
                chart_type="bar",
                x_column="region",
                y_columns=["total"],
                span=8,
            ),
            DashboardPanel(
                title="Share",
                sql="SELECT region, SUM(amount) AS total FROM sales GROUP BY region",
                chart_type="pie",
                label_column="region",
                value_column="total",
                span=4,
            ),
        ],
    )
    monkeypatch.setattr(llm_module, "_default_client", StubLLM(plan))
    fake = FakeEngine()

    async def _fake_loader(_workspace_id):
        return fake

    monkeypatch.setattr(dashboard_builder, "build_engine_for_workspace", _fake_loader)
    yield fake
    monkeypatch.setattr(llm_module, "_default_client", None)


@pytest.mark.asyncio
async def test_dashboard_composes_panels(_wire: FakeEngine) -> None:
    state = {
        "user_message": "give me a sales overview",
        "resolved_workspace_id": uuid4(),
        "intent": "dashboard",
        "schema_bundle": _bundle(),
    }
    out = await dashboard_builder.run(state)
    dash = out["chart"]
    assert dash.type == "dashboard"
    assert dash.title == "Sales overview"
    assert len(dash.children) == 2
    assert dash.children[0].spec.type == "bar"
    assert dash.children[0].span == 8
    assert dash.children[1].spec.type == "pie"
    # Both panels actually executed their SQL
    assert len(_wire.executed) == 2


@pytest.mark.asyncio
async def test_invalid_panel_sql_is_skipped(monkeypatch) -> None:
    plan = DashboardPlan(
        dialect="sqlite",
        title="Mixed",
        panels=[
            DashboardPanel(
                title="good",
                sql="SELECT region, SUM(amount) AS total FROM sales GROUP BY region",
                chart_type="bar",
                x_column="region",
                y_columns=["total"],
            ),
            DashboardPanel(
                title="evil",
                sql="DROP TABLE sales",  # rejected by validator -> skipped
                chart_type="table",
            ),
        ],
    )
    monkeypatch.setattr(llm_module, "_default_client", StubLLM(plan))
    fake = FakeEngine()

    async def _fake_loader(_workspace_id):
        return fake

    monkeypatch.setattr(dashboard_builder, "build_engine_for_workspace", _fake_loader)

    out = await dashboard_builder.run(
        {
            "user_message": "x",
            "resolved_workspace_id": uuid4(),
            "intent": "dashboard",
            "schema_bundle": _bundle(),
        }
    )
    monkeypatch.setattr(llm_module, "_default_client", None)
    dash = out["chart"]
    assert dash.type == "dashboard"
    # Only the valid panel survived; the DROP was never executed.
    assert len(dash.children) == 1
    assert fake.executed == [
        "SELECT region, SUM(amount) AS total FROM sales GROUP BY region LIMIT 1000"
    ]
