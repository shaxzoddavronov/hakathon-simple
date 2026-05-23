from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IntentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Literal["chitchat", "metadata", "data_query", "dashboard", "clarify"]
    workspace_hint: str | None = Field(
        default=None,
        description="Workspace name extracted from @ mention or bare-word match.",
    )


class SqlPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dialect: Literal["postgres", "sqlite"]
    sql: str = Field(
        description="A single read-only SELECT. Validator will reject DML/DDL."
    )
    rationale: str = Field(
        description="One sentence: why this SQL answers the user's question."
    )
    expected_columns: list[str] = Field(
        description="Column names the planner expects to see in the result."
    )


class KeyNumber(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    value: float | str
    unit: str | None = None


class AnswerDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(
        description="One-line summary. Used as page title and chat preview."
    )
    body_md: str = Field(
        description="2-4 sentence markdown narrative referencing the result."
    )
    key_numbers: list[KeyNumber] = Field(
        default_factory=list,
        description="Pull-out metrics highlighted in the UI.",
    )
