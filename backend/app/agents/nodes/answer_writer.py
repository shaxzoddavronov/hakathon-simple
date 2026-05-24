from __future__ import annotations

from app.agents.llm import agent_llm
from app.agents.state import GraphState
from app.engines.base import ResultSet
from app.schemas.llm_io import AnswerDraft

_SYSTEM = (
    "You are an analyst who writes 2-3 sentence summaries of SQL results. "
    "Use only the numbers and labels you are shown. Do not invent values. "
    "Highlight the key takeaway in the headline; back it up in body_md."
)


def _result_shape(rs: ResultSet | None) -> str:
    if rs is None:
        return "no result"
    return (
        f"columns: {rs.columns}\n"
        f"row_count: {rs.row_count}\n"
        f"sample_rows (first 5): {rs.rows[:5]}\n"
    )


async def run(state: GraphState) -> GraphState:
    if state.get("no_workspace"):
        # No database connected — the agent (LLM) explains, not a hardcoded string.
        llm = agent_llm(state)
        draft = await llm.structured(
            [
                {
                    "role": "system",
                    "content": (
                        "The user has NOT connected any database to QueryMind yet. "
                        "In 1-2 friendly sentences, explain that they need to connect "
                        "a database (a 'workspace') first before you can answer "
                        "questions about their data, and invite them to do so. Do not "
                        "invent any data or tables."
                    ),
                },
                {"role": "user", "content": state.get("user_message", "")},
            ],
            AnswerDraft,
        )
        return {"answer": draft}

    rs = state.get("result")
    if rs is None and state.get("intent") in {"chitchat", "metadata"}:
        # No data — produce a short conversational answer.
        llm = agent_llm(state)
        draft = await llm.structured(
            [
                {
                    "role": "system",
                    "content": (
                        "You answer brief conversational and metadata questions about a "
                        "connected database. Keep it short and helpful."
                    ),
                },
                {"role": "user", "content": state.get("user_message", "")},
            ],
            AnswerDraft,
        )
        return {"answer": draft}

    if rs is None:
        return {"answer": AnswerDraft(headline="No result.", body_md="The query returned no rows.")}

    llm = agent_llm(state)
    prompt = (
        f"Question: {state.get('user_message','')}\n\n"
        f"Result shape:\n{_result_shape(rs)}\n\n"
        "Return an AnswerDraft."
    )
    draft = await llm.structured(
        [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        AnswerDraft,
    )
    return {"answer": draft}
