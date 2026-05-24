"""Standalone vLLM integration probe — run BEFORE booting the full stack.

Sends the exact structured-output call shape the agent uses
(response_format json_schema + strict) to your vLLM server and reports
whether guided JSON decoding actually works. If this fails, every
LLM-driven node will fail too — so check it here first, in isolation.

Usage:
    cd backend
    VLLM_ENDPOINT=http://localhost:8000/v1 VLLM_MODEL=Qwen/Qwen2.5-0.5B-Instruct \
      python scripts/check_vllm.py
"""
from __future__ import annotations

import asyncio
import sys

from app.agents.llm import LLMClient
from app.schemas.llm_io import IntentDecision, SqlPlan


async def main() -> int:
    client = LLMClient()
    print(f"endpoint: {client._endpoint}")  # noqa: SLF001 — diagnostic
    print(f"model:    {client.model}\n")

    print("[1/3] reachability (/models)...", flush=True)
    if not await client.is_ready():
        print("  ✗ vLLM not reachable. Is it serving? Check the endpoint/port.")
        return 1
    print("  ✓ reachable\n")

    print("[2/3] simple guided JSON (IntentDecision)...", flush=True)
    try:
        decision = await client.structured(
            [
                {"role": "system", "content": "Classify the message intent."},
                {"role": "user", "content": "show me total revenue by region"},
            ],
            IntentDecision,
        )
        print(f"  ✓ parsed: intent={decision.intent!r} hint={decision.workspace_hint!r}\n")
    except Exception as e:
        print(f"  ✗ FAILED: {type(e).__name__}: {e}")
        print("    If this is a 400/422, your vLLM build likely doesn't accept")
        print("    response_format=json_schema. Try upgrading vLLM, or switch")
        print("    LLMClient.structured to extra_body={'guided_json': schema}.\n")
        return 2

    print("[3/3] nested schema with a list (SqlPlan)...", flush=True)
    try:
        plan = await client.structured(
            [
                {"role": "system", "content": "Write one read-only SELECT for the question."},
                {
                    "role": "user",
                    "content": "Table sales(region text, amount numeric). "
                    "Question: total revenue per region. Return a SqlPlan.",
                },
            ],
            SqlPlan,
        )
        print(f"  ✓ parsed: dialect={plan.dialect!r}")
        print(f"    sql: {plan.sql}")
        print(f"    expected_columns: {plan.expected_columns}\n")
    except Exception as e:
        print(f"  ✗ FAILED on the nested schema: {type(e).__name__}: {e}")
        print("    Simple schemas work but lists/optionals don't — likely an")
        print("    xgrammar limitation on this model. Note which schemas break.\n")
        return 3

    print("All checks passed. vLLM guided JSON works with the agent's call shape.")
    print("Note: this proves the *integration*, not the model's SQL *quality* —")
    print("watch query_history for validator rejections once you run real queries.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
