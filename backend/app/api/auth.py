"""Auth router (login / register / refresh).

Stub for Wave 1 — routes land in a later wave alongside the JWT helpers
in ``app/api/deps.py``.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])
