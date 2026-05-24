"""chat_sessions.workspace_id nullable

A chat session can exist before any workspace is connected, so the agent
can answer "connect a database first". Drop the NOT NULL constraint.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-24 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("chat_sessions", "workspace_id", nullable=True)


def downgrade() -> None:
    op.alter_column("chat_sessions", "workspace_id", nullable=False)
