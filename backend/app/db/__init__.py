"""Database package — exposes the declarative ``Base`` for ORM models.

Defining ``Base`` here (rather than inside ``models.py``) lets Alembic's
``env.py`` import the metadata without triggering the full model module
graph during edge cases like ``alembic init``.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all QueryMind ORM models."""


__all__ = ["Base"]
