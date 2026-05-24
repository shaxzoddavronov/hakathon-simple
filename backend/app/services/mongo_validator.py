"""Read-only validator for MongoDB aggregation pipelines (the parse layer
for the mongo_agg query kind, analogous to the SQL readonly_validator).

Rejects write stages and JS-executing operators anywhere in the pipeline.
"""
from __future__ import annotations

import json
from typing import Any

from app.engines.base import ValidationFinding, ValidationResult

# Write stages and server-side-JS / arbitrary-code operators.
_FORBIDDEN = {
    "$out",  # writes results to a collection
    "$merge",  # writes/updates a collection
    "$function",  # runs server-side JS
    "$accumulator",  # server-side JS accumulator
    "$where",  # server-side JS predicate
}


def _scan(node: Any, findings: list[ValidationFinding]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if k in _FORBIDDEN:
                findings.append(
                    ValidationFinding(
                        code="FORBIDDEN_OP",
                        message=f"Operator/stage {k} is not allowed (read-only).",
                        node_kind=k,
                    )
                )
            _scan(v, findings)
    elif isinstance(node, list):
        for item in node:
            _scan(item, findings)


def validate_mongo_pipeline(pipeline_json: str) -> ValidationResult:
    try:
        pipeline = json.loads(pipeline_json)
    except Exception as e:
        return ValidationResult(
            ok=False,
            findings=[ValidationFinding(code="PARSE_ERROR", message=str(e))],
        )
    if not isinstance(pipeline, list):
        return ValidationResult(
            ok=False,
            findings=[
                ValidationFinding(
                    code="NOT_A_PIPELINE",
                    message="Pipeline must be a JSON array of aggregation stages.",
                )
            ],
        )
    if not all(isinstance(stage, dict) for stage in pipeline):
        return ValidationResult(
            ok=False,
            findings=[
                ValidationFinding(
                    code="BAD_STAGE", message="Each pipeline stage must be an object."
                )
            ],
        )
    findings: list[ValidationFinding] = []
    _scan(pipeline, findings)
    return ValidationResult(ok=len(findings) == 0, findings=findings)


__all__ = ["validate_mongo_pipeline"]
