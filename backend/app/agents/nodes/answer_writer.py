from __future__ import annotations

from app.agents.llm import get_llm
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
    rs = state.get("result")
    if rs is None and state.get("intent") in {"chitchat", "metadata"}:
        # No data — produce a short conversational answer.
        llm = get_llm()
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

    llm = get_llm()
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
