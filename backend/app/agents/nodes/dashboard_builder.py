from __future__ import annotations

import logging

from app.agents.llm import agent_llm
from app.agents.nodes.chart_designer import ChartChoice, _build_spec
from app.agents.nodes.query_planner import _schema_brief
from app.agents.state import GraphState
from app.engines.base import SchemaBundle
from app.schemas.llm_io import DashboardPanel, DashboardPlan
from app.schemas.ui_spec import Dashboard, GridChild, TextOnly, UISpec
from app.services.engine_loader import build_engine_for_workspace
from app.services.readonly_validator import validate_readonly

log = logging.getLogger(__name__)

_MAX_PANELS = 6

_SYSTEM = (
    "You design an analytics DASHBOARD: 2-6 complementary panels that together "
    "answer the user's question. Each panel is one read-only SELECT plus a chart "
    "spec (kpi for a headline number, bar/line/pie for breakdowns, table for "
    "detail). Reference only columns that exist. Vary the panels — don't repeat "
    "the same query. Choose span 1-12 so panels tile a 12-column grid."
)


def _panel_to_choice(panel: DashboardPanel) -> ChartChoice:
    return ChartChoice(
        chart_type=panel.chart_type,
        title=panel.title,
        x_column=panel.x_column,
        y_columns=panel.y_columns,
        label_column=panel.label_column,
        value_column=panel.value_column,
    )


async def run(state: GraphState) -> GraphState:
    workspace_id = state.get("resolved_workspace_id")
    bundle: SchemaBundle | None = state.get("schema_bundle")
    if workspace_id is None or bundle is None:
        return {"error_message": "dashboard needs a resolved workspace and schema"}

    llm = agent_llm(state)
    keep = state.get("pruned_table_qnames")
    try:
        plan = await llm.structured(
            [
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": f"Question: {state.get('user_message','')}\n\n"
                    f"Schema:\n{_schema_brief(bundle, keep)}\n\nReturn a DashboardPlan.",
                },
            ],
            DashboardPlan,
        )
    except Exception as exc:
        log.exception("dashboard plan failed")
        return {"error_message": f"Could not plan a dashboard: {exc}"}

    panels = plan.panels[:_MAX_PANELS]
    children = await _execute_panels(workspace_id, plan.dialect, panels)
    if not children:
        return {"error_message": "No dashboard panels could be built."}

    dashboard: UISpec = Dashboard(type="dashboard", title=plan.title, children=children)
    return {"chart": dashboard, "sql_executed": _join_sql(panels)}


async def _execute_panels(workspace_id, dialect: str, panels: list[DashboardPanel]) -> list[GridChild]:
    try:
        engine = await build_engine_for_workspace(workspace_id)
    except Exception as exc:
        log.exception("dashboard engine load failed")
        return [
            GridChild(
                span=12,
                spec=TextOnly(type="text_only", body_md=f"⚠️ Could not connect: {exc}"),
            )
        ]

    children: list[GridChild] = []
    try:
        for panel in panels:
            validation = validate_readonly(panel.sql, dialect=dialect)
            if not validation.ok:
                # Skip a rejected panel rather than fail the whole dashboard.
                log.warning("dashboard panel rejected: %s", panel.title)
                continue
            sql = validation.rewritten_sql or panel.sql
            try:
                rs = await engine.execute(sql)
            except Exception:
                log.exception("dashboard panel execution failed: %s", panel.title)
                continue
            if rs.row_count == 0:
                continue
            spec = _build_spec(_panel_to_choice(panel), rs)
            children.append(GridChild(span=max(1, min(12, panel.span)), spec=spec))
    finally:
        await engine.aclose()

    return children


def _join_sql(panels: list[DashboardPanel]) -> str:
    return "\n\n".join(f"-- {p.title}\n{p.sql}" for p in panels)
