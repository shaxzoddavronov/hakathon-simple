from __future__ import annotations

from app.agents.llm import agent_llm
from app.agents.state import GraphState
from app.engines.base import SchemaBundle
from app.schemas.llm_io import MongoAggPlan, SqlPlan

_SYSTEM = (
    "You are a SQL planner for a strict READ-ONLY analytics tool. "
    "Generate exactly one SELECT (with optional WITH/CTEs) that answers "
    "the user's question against the provided schema. "
    "Rules: SELECT only, no DML/DDL, no system tables, no functions like "
    "pg_sleep or load_file. Reference only columns that exist. "
    "Prefer concise queries; do not include comments."
)

_MONGO_SYSTEM = (
    "You are a MongoDB aggregation planner for a strict READ-ONLY analytics "
    "tool. Given the collections and their fields, produce ONE aggregation "
    "pipeline that answers the question. Set `collection` to the target "
    "collection and `pipeline_json` to the pipeline as a JSON array string "
    '(e.g. \'[{"$group":{"_id":"$region","total":{"$sum":"$amount"}}}]\'). '
    "Read-only: never use $out, $merge, $function, $accumulator, or $where. "
    "Reference only fields that exist; prefer $match/$group/$project/$sort/$limit."
)


def _schema_brief(bundle: SchemaBundle | None, keep: list[str] | None) -> str:
    if bundle is None:
        return "(no schema loaded)"
    keep_set = set(keep or [])
    lines: list[str] = [f"dialect={bundle.dialect}"]
    for t in bundle.tables:
        qn = f"{t.schema}.{t.name}"
        if keep_set and qn not in keep_set:
            continue
        cols = ", ".join(f"{c.name}:{c.data_type}" for c in t.columns)
        line = f"- {qn}({cols})"
        if t.foreign_keys:
            fks = "; ".join(
                f"{','.join(fk.from_columns)}->{fk.to_table}({','.join(fk.to_columns)})"
                for fk in t.foreign_keys
            )
            line += f"  fks: {fks}"
        lines.append(line)
    # Categorical samples help the planner pick the right values.
    sample_lines: list[str] = []
    for qn, cols in bundle.samples.items():
        if keep_set and qn not in keep_set:
            continue
        for cname, s in cols.items():
            if s.distinct_values:
                vals = ", ".join(repr(v) for v in s.distinct_values[:8])
                sample_lines.append(f"  {qn}.{cname} in {{ {vals}{', ...' if s.distinct_truncated else ''} }}")
    if sample_lines:
        lines.append("samples:")
        lines.extend(sample_lines[:30])
    return "\n".join(lines)


async def run(state: GraphState) -> GraphState:
    attempts = int(state.get("planner_attempts", 0)) + 1
    bundle = state.get("schema_bundle")
    keep = state.get("pruned_table_qnames")

    feedback: list[str] = []
    if state.get("last_validation_error"):
        feedback.append(f"Previous attempt rejected by validator: {state['last_validation_error']}")
    if state.get("last_executor_error"):
        feedback.append(f"Previous attempt failed at execution: {state['last_executor_error']}")

    fb = ("\n".join(feedback) + "\n\n") if feedback else ""
    llm = agent_llm(state)

    if state.get("query_kind") == "mongo_agg":
        prompt_user = (
            f"Question: {state.get('user_message','')}\n\n"
            f"Collections (fields):\n{_schema_brief(bundle, keep)}\n\n"
            + fb
            + "Return a MongoAggPlan."
        )
        plan = await llm.structured(
            [
                {"role": "system", "content": _MONGO_SYSTEM},
                {"role": "user", "content": prompt_user},
            ],
            MongoAggPlan,
        )
    else:
        prompt_user = (
            f"Question: {state.get('user_message','')}\n\n"
            f"Schema:\n{_schema_brief(bundle, keep)}\n\n"
            + fb
            + "Return a SqlPlan."
        )
        plan = await llm.structured(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt_user},
            ],
            SqlPlan,
        )
    return {
        "plan": plan,
        "planner_attempts": attempts,
        # Clear stale feedback for the next turn
        "last_validation_error": None,
        "last_executor_error": None,
    }
