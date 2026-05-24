"""expand dialect CHECK constraints for multi-backend support

Original CHECKs limited dialect to ('postgres','sqlite'). Allow the new
engines (clickhouse, oracle, elasticsearch, mongodb) on workspaces and
query_history.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-24 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW = "dialect IN ('postgres','sqlite','clickhouse','oracle','elasticsearch','mongodb')"
_OLD = "dialect IN ('postgres','sqlite')"


def _swap(table: str, name: str, expr: str) -> None:
    op.drop_constraint(name, table, type_="check")
    op.create_check_constraint(name, table, expr)


def upgrade() -> None:
    _swap("workspaces", "ck_workspaces_dialect", _NEW)
    _swap("query_history", "ck_query_history_dialect", _NEW)


def downgrade() -> None:
    _swap("workspaces", "ck_workspaces_dialect", _OLD)
    _swap("query_history", "ck_query_history_dialect", _OLD)
